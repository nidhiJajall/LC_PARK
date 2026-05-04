"""
Service layer for the lc_request module.

Handles OCR extraction, LC Request CRUD, and list/detail retrieval.
All DB writes use django-reversion for full audit history.
"""
import json
import logging
from decimal import Decimal
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

    @staticmethod
    def _coerce_int(val):
        """Return int or None; treats null sentinels as None."""
        if val in _NULL_SENTINELS or val is None:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_decimal(val):
        """Return Decimal or None; treats null sentinels as None."""
        if val in _NULL_SENTINELS or val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    @staticmethod
    def _coerce_date(val):
        """Parse OCR (DD.MM.YYYY) or frontend (YYYY-MM-DD) date strings. Returns date or None."""
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
        return None

    def _extract_lc_detail_fields(self, data: dict) -> dict:
        """
        Map incoming request keys to LcDetails model fields with type coercion.
        Uses Constants.FULL_FIELD_MAP — the single source of truth for key→field mapping.
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
        return result

    @staticmethod
    def _save_so_details(lc_instance: LcRequest, so_details_raw):
        """Resolve SO numbers from request data and set the M2M relation."""
        if not so_details_raw:
            return
        try:
            so_list = json.loads(so_details_raw) if isinstance(so_details_raw, str) else so_details_raw
        except Exception:
            logger.warning('Could not parse so_details for LcRequest #%s', lc_instance.pk)
            return
        if not isinstance(so_list, list):
            return

        from masters.models.Sodata import Sodata
        so_numbers = [row.get("so_number") for row in so_list if row.get("so_number")]
        sodata_qs  = Sodata.objects.filter(so_number__in=so_numbers)
        lc_instance.so_data.set(sodata_qs)
        logger.info('Set %d SO(s) on LcRequest #%s', sodata_qs.count(), lc_instance.pk)

    @staticmethod
    def _find_y_entry(n_entry: LcDetails):
        """Return the Y (OCR) LcDetails entry matching this N entry's instrument number."""
        if not n_entry or not n_entry.instrument_number:
            return None
        return LcDetails.objects.filter(
            instrument_number=n_entry.instrument_number,
            extracted_flag='Y',
        ).first()

    # ── OCR ───────────────────────────────────────────────────────────────────

    def extract_ocr_data(self, request) -> Response:
        """Forward the uploaded PDF to the OCR service and return its response."""
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info('OCR extraction requested for file: %s', uploaded_file.name)
        try:
            ocr_resp = requests.post(
                Constants.OCR_URL,
                files={"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)},
                data={"project_name": Constants.OCR_PROJECT_NAME},
                timeout=Constants.OCR_TIMEOUT_SECS,
                verify=False,
            )
            logger.info('OCR service responded with status %s', ocr_resp.status_code)
            return Response(ocr_resp.json(), status=ocr_resp.status_code)
        except Exception as exc:
            logger.error('OCR service error: %s', exc)
            return Response({"error": "OCR service unavailable"}, status=status.HTTP_502_BAD_GATEWAY)

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_lc_request(self, request) -> Response:
        """Create a new LcRequest with paired Y/N LcDetails entries and optional file."""
        data  = request.data
        files = request.FILES
        lc_fields = self._extract_lc_detail_fields(data)

        with reversion.create_revision():
            y_entry = LcDetails.objects.create(**lc_fields, extracted_flag='Y')
            n_entry = LcDetails.objects.create(**lc_fields, extracted_flag='N')

            lc_instance = LcRequest.objects.create(
                lc_details=n_entry,
                interest_free_credit_days=self._coerce_int(data.get("interest_free_credit_days")),
                interest_charges=self._coerce_decimal(data.get("interest_charges")),
                usance_period=self._coerce_int(data.get("usance_period")),
                request_status=data.get("status", Constants.STATUS_DRAFT),
                created_by=data.get("created_by", ""),
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

            reversion.set_comment("Version 1 — initial save")

        logger.info('Created LcRequest #%s (status: %s)', lc_instance.pk, lc_instance.request_status)
        return Response(LCRequestDetailSerializer(lc_instance).data, status=status.HTTP_201_CREATED)

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_lc_request(self, request, pk: int) -> Response:
        """Update an existing LcRequest, its N-entry details, SO links, and optional file."""
        data  = request.data
        files = request.FILES

        try:
            lc_instance = LcRequest.objects.select_related("lc_details").get(pk=pk)
        except LcRequest.DoesNotExist:
            logger.warning('LcRequest #%s not found for update', pk)
            return Response({"error": "LC Request not found."}, status=status.HTTP_404_NOT_FOUND)

        lc_fields = self._extract_lc_detail_fields(data)

        with reversion.create_revision():
            n_entry = lc_instance.lc_details
            for field, value in lc_fields.items():
                setattr(n_entry, field, value)
            n_entry.save()

            if data.get("interest_free_credit_days") is not None:
                lc_instance.interest_free_credit_days = self._coerce_int(data.get("interest_free_credit_days"))
            if data.get("interest_charges") is not None:
                lc_instance.interest_charges = self._coerce_decimal(data.get("interest_charges"))
            if data.get("usance_period") is not None:
                lc_instance.usance_period = self._coerce_int(data.get("usance_period"))
            if data.get("status"):
                lc_instance.request_status = data.get("status")
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

            reversion.set_comment("Updated — status: %s" % lc_instance.request_status)

        logger.info('Updated LcRequest #%s (status: %s)', pk, lc_instance.request_status)
        return Response(LCRequestDetailSerializer(lc_instance).data)

    # ── LIST ──────────────────────────────────────────────────────────────────

    def get_lc_list(self, query_params) -> Response:
        """Return a paginated, optionally filtered/searched list of LcRequests."""
        qs = (
            LcRequest.objects
            .prefetch_related("so_data")
            .select_related("lc_details")
            .order_by("-created_date")
        )

        if search := query_params.get("search"):
            qs = qs.filter(
                Q(lc_details__instrument_number__icontains=search) |
                Q(request_status__icontains=search) |
                Q(so_data__so_number__icontains=search)
            ).distinct()

        if query_params.get("filter"):
            if st := query_params.get("request_status"):
                qs = qs.filter(request_status=st)

        paginator = Paginator(qs, int(query_params.get("pageSize", 20)))
        page_obj  = paginator.get_page(int(query_params.get("page", 1)))

        serializer = LCRequestListSerializer(page_obj.object_list, many=True)
        return Response({"total": paginator.count, "results": serializer.data})

    # ── DETAIL ────────────────────────────────────────────────────────────────

    def get_lc_by_id(self, pk: int) -> Response:
        """Return full detail for a single LcRequest by primary key."""
        try:
            instance = (
                LcRequest.objects
                .select_related("lc_details")
                .prefetch_related("so_data")
                .get(pk=pk)
            )
            return Response(LCRequestDetailSerializer(instance).data)
        except LcRequest.DoesNotExist:
            logger.warning('LcRequest #%s not found', pk)
            return Response({"error": "LC Request not found."}, status=status.HTTP_404_NOT_FOUND)