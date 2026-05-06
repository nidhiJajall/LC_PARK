"""
Service layer for the lc_request module.

Handles OCR extraction, LC Request CRUD, and list/detail retrieval.
All DB writes use django-reversion for full audit history.

Logging convention:
  INFO  — operation start, success, record counts
  WARNING — recoverable issues (not found, parse failures, skipped steps)
  ERROR — unexpected failures that prevent the operation completing
  DEBUG — raw values, field maps, coercion details
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

import requests
import reversion
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from .models import LcRequest, LcDetails, LcFiles
from .serializers import LCRequestListSerializer, LCRequestDetailSerializer
from lc_request import Constants

logger = logging.getLogger(__name__)

_INT_FIELDS     = frozenset({"unance_period", "negotiation_days"})
_DECIMAL_FIELDS = frozenset({"grace_value"})
_NULL_SENTINELS = frozenset({"", "Invalid Date", "null", "undefined"})


class LCRequestService:
    """Service class for all LcRequest business operations."""

    # ── Type coercion helpers ─────────────────────────────────────────────────

    @staticmethod
    def _coerce_int(val) -> int | None:
        """
        Return int or None; treats null sentinels as None.

        Args:
            val: Raw value from request data.

        Returns:
            Parsed integer or None.
        """
        if val in _NULL_SENTINELS or val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            logger.debug('_coerce_int: could not parse %r as int — returning None', val)
            return None

    @staticmethod
    def _coerce_decimal(val) -> Decimal | None:
        """
        Return Decimal or None; treats null sentinels as None.

        Args:
            val: Raw value from request data.

        Returns:
            Parsed Decimal or None.
        """
        if val in _NULL_SENTINELS or val is None:
            return None
        try:
            return Decimal(str(val))
        except (TypeError, ValueError, InvalidOperation):
            logger.debug('_coerce_decimal: could not parse %r as Decimal — returning None', val)
            return None

    @staticmethod
    def _coerce_date(val):
        """
        Parse OCR (DD.MM.YYYY) or frontend (YYYY-MM-DD) date strings.

        Args:
            val: Raw date string from OCR or frontend.

        Returns:
            datetime.date or None.
        """
        if not val or val in _NULL_SENTINELS:
            return None
        if isinstance(val, str):
            if '.' in val:
                try:
                    return datetime.strptime(val, "%d.%m.%Y").date()
                except ValueError:
                    pass
            if '-' in val:
                try:
                    return datetime.strptime(val, "%Y-%m-%d").date()
                except ValueError:
                    pass
        logger.debug('_coerce_date: unrecognised date format %r — returning None', val)
        return None

    # ── Field extraction ──────────────────────────────────────────────────────

    def _extract_lc_detail_fields(self, data: dict) -> dict:
        """
        Map incoming request keys to LcDetails model fields with type coercion.

        Uses Constants.FULL_FIELD_MAP as the single source of truth for
        key → field mapping. Handles both OCR key names and model field names.

        Args:
            data: Raw request data dict (QueryDict or plain dict).

        Returns:
            Dict of model field names → coerced values, ready for LcDetails.
        """
        result = {}
        for fe_key, model_field in Constants.FULL_FIELD_MAP.items():
            raw = data.get(fe_key)
            if raw is None:
                continue
            if model_field in Constants.OCR_DATE_FIELDS:
                result[model_field] = self._coerce_date(raw)
            elif model_field in _INT_FIELDS:
                result[model_field] = self._coerce_int(raw)
            elif model_field in _DECIMAL_FIELDS:
                result[model_field] = self._coerce_decimal(raw)
            else:
                result[model_field] = raw if raw not in _NULL_SENTINELS else None

        logger.debug(
            '_extract_lc_detail_fields: mapped %d fields from %d input keys',
            len(result), len(data),
        )
        return result

    # ── SO helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _save_so_details(lc_instance: LcRequest, so_details_raw) -> None:
        """
        Resolve SO numbers from request data and set the M2M relation.

        Args:
            lc_instance: The LcRequest to attach SO data to.
            so_details_raw: JSON string or list of SO dicts from the request.
        """
        if not so_details_raw:
            logger.debug(
                '_save_so_details: no SO data provided for LcRequest #%s — skipping',
                lc_instance.pk,
            )
            return

        try:
            so_list = (
                json.loads(so_details_raw)
                if isinstance(so_details_raw, str)
                else so_details_raw
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                '_save_so_details: failed to parse so_details for LcRequest #%s'
                ' -- error: %s',
                lc_instance.pk, exc,
            )
            return

        if not isinstance(so_list, list):
            logger.warning(
                '_save_so_details: so_details is not a list for LcRequest #%s'
                ' -- type: %s',
                lc_instance.pk, type(so_list).__name__,
            )
            return

        from masters.models.Sodata import Sodata

        so_numbers = [row.get("so_number") for row in so_list if row.get("so_number")]
        logger.debug(
            '_save_so_details: resolving %d SO numbers for LcRequest #%s -- %s',
            len(so_numbers), lc_instance.pk, so_numbers,
        )

        sodata_qs = Sodata.objects.filter(so_number__in=so_numbers)
        matched   = sodata_qs.count()

        if matched != len(so_numbers):
            unmatched = set(so_numbers) - set(
                sodata_qs.values_list('so_number', flat=True)
            )
            logger.warning(
                '_save_so_details: %d SO(s) not found in master data'
                ' for LcRequest #%s -- missing: %s',
                len(unmatched), lc_instance.pk, list(unmatched),
            )

        lc_instance.so_data.set(sodata_qs)
        logger.info(
            '_save_so_details: linked %d SO(s) to LcRequest #%s',
            matched, lc_instance.pk,
        )

    @staticmethod
    def _find_y_entry(n_entry: LcDetails) -> LcDetails | None:
        """
        Return the Y (OCR) LcDetails entry matching this N entry's instrument number.

        Args:
            n_entry: The user-editable (N-flag) LcDetails instance.

        Returns:
            Matching Y-flag LcDetails or None.
        """
        if not n_entry or not n_entry.instrument_number:
            logger.debug('_find_y_entry: n_entry has no instrument_number — returning None')
            return None

        y_entry = LcDetails.objects.filter(
            instrument_number=n_entry.instrument_number,
            extracted_flag='Y',
        ).first()

        if not y_entry:
            logger.warning(
                '_find_y_entry: no Y-entry found for instrument_number %s',
                n_entry.instrument_number,
            )
        return y_entry

    # ── OCR ───────────────────────────────────────────────────────────────────

    def extract_ocr_data(self, request) -> Response:
        """
        Forward the uploaded PDF to the OCR service and return its response.

        Args:
            request: DRF request with FILES['file'] containing the PDF.

        Returns:
            Response: OCR service JSON response or error.
        """
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            logger.warning('extract_ocr_data: no file in request')
            return Response(
                {"error": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            'extract_ocr_data: sending file to OCR -- name: %s -- size: %s bytes'
            ' -- content_type: %s',
            uploaded_file.name, uploaded_file.size, uploaded_file.content_type,
        )

        try:
            ocr_resp = requests.post(
                Constants.OCR_URL,
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.read(),
                        uploaded_file.content_type,
                    )
                },
                data={"project_name": Constants.OCR_PROJECT_NAME},
                timeout=Constants.OCR_TIMEOUT_SECS,
                verify=False,
            )
            logger.info(
                'extract_ocr_data: OCR service responded -- status: %s',
                ocr_resp.status_code,
            )
            if not ocr_resp.ok:
                logger.warning(
                    'extract_ocr_data: OCR service returned non-2xx -- status: %s'
                    ' -- body: %s',
                    ocr_resp.status_code, ocr_resp.text[:200],
                )
            return Response(ocr_resp.json(), status=ocr_resp.status_code)

        except requests.Timeout:
            logger.error(
                'extract_ocr_data: OCR service timed out after %s seconds'
                ' -- file: %s',
                Constants.OCR_TIMEOUT_SECS, uploaded_file.name,
            )
            return Response(
                {"error": "OCR service timed out"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.error(
                'extract_ocr_data: OCR service connection error -- %s', exc,
            )
            return Response(
                {"error": "OCR service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_lc_request(self, request) -> Response:
        """
        Create a new LcRequest with paired Y/N LcDetails entries and optional file.

        Y entry = OCR-extracted (immutable reference).
        N entry = user-editable copy (linked to LcRequest).

        Args:
            request: DRF request with LC fields and optional PDF in FILES.

        Returns:
            Response: Created LcRequest detail (HTTP 201) or error.
        """
        data      = request.data
        files     = request.FILES
        lc_fields = self._extract_lc_detail_fields(data)

        logger.info(
            'create_lc_request: creating LcRequest -- user: %s -- status: %s'
            ' -- instrument: %s -- so_details_present: %s -- file_present: %s',
            data.get('created_by', 'unknown'),
            data.get('status', Constants.STATUS_DRAFT),
            lc_fields.get('instrument_number', '—'),
            bool(data.get('so_details')),
            bool(files.get('file')),
        )

        with reversion.create_revision():
            y_entry = LcDetails.objects.create(**lc_fields, extracted_flag='Y')
            n_entry = LcDetails.objects.create(**lc_fields, extracted_flag='N')
            logger.debug(
                'create_lc_request: created LcDetails Y=#%s N=#%s',
                y_entry.pk, n_entry.pk,
            )

            lc_instance = LcRequest.objects.create(
                lc_details=n_entry,
                interest_free_credit_days=self._coerce_int(
                    data.get("interest_free_credit_days")
                ),
                interest_charges=self._coerce_decimal(data.get("interest_charges")),
                usance_period=self._coerce_int(data.get("usance_period")),
                request_status=data.get("status", Constants.STATUS_DRAFT),
                created_by=data.get("created_by", ""),
            )
            logger.debug(
                'create_lc_request: created LcRequest #%s', lc_instance.pk,
            )

            self._save_so_details(lc_instance, data.get("so_details"))

            if uploaded_file := files.get("file"):
                LcFiles.objects.create(
                    file=uploaded_file,
                    category=Constants.LC_DOCUMENT,
                    status="active",
                    password=data.get("password", ""),
                    lc_details=y_entry.pk,
                )
                logger.debug(
                    'create_lc_request: attached file %s to Y-entry #%s',
                    uploaded_file.name, y_entry.pk,
                )

            reversion.set_comment("Version 1 — initial save")

        logger.info(
            'create_lc_request: success -- LcRequest #%s -- status: %s',
            lc_instance.pk, lc_instance.request_status,
        )
        return Response(
            LCRequestDetailSerializer(lc_instance).data,
            status=status.HTTP_201_CREATED,
        )

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_lc_request(self, request, pk: int) -> Response:
        """
        Update an existing LcRequest, its N-entry details, SO links, and optional file.

        Args:
            request: DRF request with fields to update.
            pk: Primary key of the LcRequest to update.

        Returns:
            Response: Updated LcRequest detail or error.
        """
        data  = request.data
        files = request.FILES

        logger.info(
            'update_lc_request: updating LcRequest #%s -- status_field: %s'
            ' -- so_details_present: %s -- file_present: %s',
            pk,
            data.get('status', 'unchanged'),
            bool(data.get('so_details')),
            bool(files.get('file')),
        )

        try:
            lc_instance = (
                LcRequest.objects
                .select_related("lc_details")
                .get(pk=pk)
            )
        except LcRequest.DoesNotExist:
            logger.warning(
                'update_lc_request: LcRequest #%s not found', pk,
            )
            return Response(
                {"error": "LC Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        lc_fields = self._extract_lc_detail_fields(data)

        with reversion.create_revision():
            n_entry = lc_instance.lc_details
            for field, value in lc_fields.items():
                setattr(n_entry, field, value)
            n_entry.save()
            logger.debug(
                'update_lc_request: saved N-entry #%s with %d fields',
                n_entry.pk, len(lc_fields),
            )

            if data.get("interest_free_credit_days") is not None:
                lc_instance.interest_free_credit_days = self._coerce_int(
                    data.get("interest_free_credit_days")
                )
            if data.get("interest_charges") is not None:
                lc_instance.interest_charges = self._coerce_decimal(
                    data.get("interest_charges")
                )
            if data.get("usance_period") is not None:
                lc_instance.usance_period = self._coerce_int(data.get("usance_period"))
            if data.get("status"):
                old_status = lc_instance.request_status
                lc_instance.request_status = data.get("status")
                if old_status != lc_instance.request_status:
                    logger.info(
                        'update_lc_request: status transition -- LcRequest #%s'
                        ' -- %s → %s',
                        pk, old_status, lc_instance.request_status,
                    )
            lc_instance.save()

            if data.get("so_details"):
                self._save_so_details(lc_instance, data.get("so_details"))

            if uploaded_file := files.get("file"):
                y_entry = self._find_y_entry(n_entry)
                if y_entry:
                    LcFiles.objects.create(
                        file=uploaded_file,
                        category=Constants.LC_ATTACHMENT,
                        status="active",
                        password=data.get("password", ""),
                        lc_details=y_entry.pk,
                    )
                    logger.debug(
                        'update_lc_request: attached file %s to Y-entry #%s',
                        uploaded_file.name, y_entry.pk,
                    )
                else:
                    logger.warning(
                        'update_lc_request: file upload skipped -- no Y-entry'
                        ' found for LcRequest #%s',
                        pk,
                    )

            reversion.set_comment(
                "Updated — status: %s" % lc_instance.request_status
            )

        logger.info(
            'update_lc_request: success -- LcRequest #%s -- status: %s',
            pk, lc_instance.request_status,
        )
        return Response(LCRequestDetailSerializer(lc_instance).data)

    # ── LIST ──────────────────────────────────────────────────────────────────

    def get_lc_list(self, query_params) -> Response:
        """
        Return a paginated, optionally filtered/searched list of LcRequests.

        Args:
            query_params: QueryDict with optional page, pageSize, search, filter,
                          request_status.

        Returns:
            Response: Dict with 'total' count and 'results' list.
        """
        page      = int(query_params.get("page", 1))
        page_size = int(query_params.get("pageSize", 20))
        search    = query_params.get("search")
        filter_on = query_params.get("filter")

        logger.info(
            'get_lc_list: page=%s pageSize=%s search=%r filter=%s',
            page, page_size, search, filter_on,
        )

        qs = (
            LcRequest.objects
            .prefetch_related("so_data")
            .select_related("lc_details")
            .order_by("-created_date")
        )

        if search:
            qs = qs.filter(
                Q(lc_details__instrument_number__icontains=search) |
                Q(request_status__icontains=search) |
                Q(so_data__so_number__icontains=search)
            ).distinct()
            logger.debug('get_lc_list: applied search filter %r', search)

        if filter_on:
            if st := query_params.get("request_status"):
                qs = qs.filter(request_status=st)
                logger.debug('get_lc_list: applied status filter %r', st)

        paginator = Paginator(qs, page_size)
        page_obj  = paginator.get_page(page)

        logger.info(
            'get_lc_list: returning page %s/%s -- %d records (total: %d)',
            page, paginator.num_pages,
            len(page_obj.object_list), paginator.count,
        )

        serializer = LCRequestListSerializer(page_obj.object_list, many=True)
        return Response({"total": paginator.count, "results": serializer.data})

    # ── DETAIL ────────────────────────────────────────────────────────────────

    def get_lc_by_id(self, pk: int) -> Response:
        """
        Return full detail for a single LcRequest by primary key.

        Args:
            pk: Primary key of the LcRequest.

        Returns:
            Response: Full LcRequest detail or 404.
        """
        logger.info('get_lc_by_id: fetching LcRequest #%s', pk)

        try:
            instance = (
                LcRequest.objects
                .select_related("lc_details")
                .prefetch_related("so_data")
                .get(pk=pk)
            )
            logger.info(
                'get_lc_by_id: found LcRequest #%s -- status: %s'
                ' -- instrument: %s',
                pk,
                instance.request_status,
                instance.lc_details.instrument_number
                if instance.lc_details else '—',
            )
            return Response(LCRequestDetailSerializer(instance).data)

        except LcRequest.DoesNotExist:
            logger.warning('get_lc_by_id: LcRequest #%s not found', pk)
            return Response(
                {"error": "LC Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
