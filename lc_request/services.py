# lc_request/services.py
# ─────────────────────────────────────────────────────────────────────────────
# ALL database and external-API logic lives here.  views.py only calls service
# methods and returns the Response — it never queries the DB or calls
# requests.post() directly.
#
# Three-table write flow (called from _save_so_details):
#
#   For each SO row in the payload:
#
#   1. LCSODetail.create()  → financial fields only
#                              (interest_free_credit_days, interest_charges,
#                               usance_period)
#   2. SODetail.create()    → Masters snapshot fields
#                              + FK  → LCRequest
#                              + OneToOne → LCSODetail (created in step 1)
#
#   On a subsequent PATCH the old SODetail rows are deleted first.
#   The CASCADE on SODetail.lc_so_detail automatically deletes the paired
#   LCSODetail rows, so no manual LCSODetail cleanup is needed.
#
# WHY three tables instead of one flat table?
#   SODetail   = Masters snapshot  (write-once, auditable, frozen at entry).
#   LCSODetail = user-entered financials (editable, revisioned separately).
#   Keeping them separate lets the LC team update financial data without
#   touching the immutable snapshot, and allows future re-sync from Masters
#   by replacing only SODetail rows without losing financial entries.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
from datetime     import datetime
from urllib.parse import urlencode

import requests
import reversion
from django.conf           import settings
from django.core.paginator import Paginator
from django.db.models      import Q
from reversion.models      import Version
from rest_framework        import status
from rest_framework.response import Response

from .models      import LCRequest, LCSODetail, SODetail
from .serializers import (
    LCRequestSerializer,
    LCRequestWriteSerializer,
    VersionSummarySerializer,
)

logger = logging.getLogger(__name__)

# ── OCR API constants ─────────────────────────────────────────────────────────
_OCR_URL          = "https://staging.amns.in/bot-ocr/api/v1/extract"
_OCR_PROJECT_NAME = "LC PARK & ENTRY"
_OCR_TIMEOUT_SECS = 60

# OCR response key → LCRequest model field name.
# Single source of truth for both _map_ocr_prediction() and the frontend.
_OCR_FIELD_MAP: dict[str, str] = {
    "Instrument_Number":          "instrument_number",
    "Form_of_DOC":                "form_of_doc",
    "Opening_Bank":               "opening_bank",
    "Opening_Date":               "opening_date",
    "Unance_Period":              "usance_period",   # OCR typo kept as-is
    "Dispatch_Upto_Date":         "dispatch_upto_date",
    "Negotiation_Days":           "negotiation_days",
    "Expiry_Date":                "expiry_date",
    "Place_TakeIn_charge":        "place_take_in_charge",
    "Place_of_Final_Destination": "place_of_final_destination",
    "Advising_Bank":              "advising_bank",
    "ES":                         "es",
    "ET":                         "et",
    "ER":                         "er",
    "Grace_Value":                "grace_value",
    "Credit_Tolerance":           "percentage_credit_amount_tolerance",
    "Cust_Name_Inv_Print":        "cust_name_inv_print",
    "Customer_Name":              "customer_name",
    "Clause_45A":                 "clause_45a",
    "Incoterm":                   "incoterm",
    "IMPS Remark":                "imps_remark",
    "Additional_Condition_47A":   "additional_condition_46a",
    "Clause78":                   "clause_78",
}

_OCR_BOOL_FIELDS: frozenset[str] = frozenset({"es", "et", "er"})
_OCR_DATE_FIELDS: frozenset[str] = frozenset(
    {"opening_date", "dispatch_upto_date", "expiry_date"}
)


class LCRequestService:
    """
    Business / persistence layer for all LC Request operations.

    Each public method maps 1-to-1 to an HTTP endpoint in views.py.
    Private helpers (``_`` prefix) are not called from views.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: OCR field mapping
    # ─────────────────────────────────────────────────────────────────────────

    def _map_ocr_prediction(self, prediction: dict) -> dict:
        """
        Convert raw OCR API ``prediction`` keys to ``LCRequest`` model field
        names and coerce types.

        Coercions applied:
            Boolean fields — ``"yes"`` / ``"no"`` → ``True`` / ``False``
            Date fields    — ``"DD.MM.YYYY"``     → ``datetime.date``

        Args:
            prediction: The ``prediction`` sub-dict from the OCR API response.

        Returns:
            Dict ready for ``LCRequest.objects.create(**mapped)``.
        """
        mapped: dict = {}

        for ocr_key, model_field in _OCR_FIELD_MAP.items():
            raw = prediction.get(ocr_key)
            if raw is None or raw == "":
                continue

            if model_field in _OCR_BOOL_FIELDS:
                mapped[model_field] = str(raw).lower() == "yes"

            elif model_field in _OCR_DATE_FIELDS:
                try:
                    mapped[model_field] = datetime.strptime(raw, "%d.%m.%Y").date()
                except (ValueError, TypeError):
                    logger.warning(
                        "OCR date parse failed: field=%s value=%r", model_field, raw
                    )
            else:
                mapped[model_field] = raw

        return mapped

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Three-table SO save
    # ─────────────────────────────────────────────────────────────────────────

    def _save_so_details(self, lc_instance: LCRequest, so_details_raw: str | None) -> None:
        """
        Persist SO rows using the three-table pattern.

        Relationship diagram::

            LCRequest  ──< SODetail  >── LCSODetail
                           (FK)            (OneToOne)

        Steps:

        1. Delete all existing ``SODetail`` rows for *lc_instance*.
           The ``on_delete=CASCADE`` on ``SODetail.lc_so_detail`` automatically
           deletes the paired ``LCSODetail`` rows — no manual cleanup needed.

        2. For each SO dict in the payload:
           a. Create ``LCSODetail`` first (no FK to LCRequest; purely financial).
           b. Create ``SODetail`` referencing both ``lc_instance`` and the
              ``LCSODetail`` just created.

        WHY create ``LCSODetail`` before ``SODetail``?
          ``SODetail.lc_so_detail`` is a FK, so the ``LCSODetail`` row must
          already have a PK before ``SODetail`` can reference it.

        WHY delete-all-then-insert instead of per-row upsert?
          The frontend always sends the *full* current SO list.  A full
          replace is simpler and avoids partial-update edge cases (e.g. a row
          the user removed from the list lingering in the DB).

        Args:
            lc_instance:    The parent ``LCRequest`` being saved.
            so_details_raw: JSON string ``[{so_number, company_code, …}, …]``.
                            Silently no-ops if ``None`` or unparseable.
        """
        if not so_details_raw:
            return

        try:
            so_list = json.loads(so_details_raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("_save_so_details: unparseable so_details_raw — skipped")
            return

        if not isinstance(so_list, list):
            return

        # ── 1. Wipe old rows (CASCADE deletes linked LCSODetail too) ─────────
        SODetail.objects.filter(lc_request=lc_instance).delete()

        # ── 2. Re-create from payload ─────────────────────────────────────────
        for row in so_list:
            cust_ref_date = row.get("cust_reference_date") or None

            # a) Financial record — standalone, no FK to LCRequest
            lc_so_detail = LCSODetail.objects.create(
                interest_free_credit_days = row.get("interest_free_credit_days"),
                interest_charges          = row.get("interest_charges"),
                usance_period             = row.get("usance_period"),
            )

            # b) Snapshot record — bridges LCRequest ↔ LCSODetail
            SODetail.objects.create(
                lc_request   = lc_instance,
                lc_so_detail = lc_so_detail,

                # Masters snapshot (frozen at entry time)
                so_number           = row.get("so_number", ""),
                company_code        = row.get("company_code"),
                plant_code          = row.get("plant_code"),
                customer_code       = row.get("customer_code"),
                ship_to_party       = row.get("ship_to_party"),
                so_value            = row.get("so_value"),
                pyt_terms           = row.get("pyt_terms"),
                remarks             = row.get("remarks"),
                cust_reference      = row.get("cust_reference"),
                cust_reference_date = cust_ref_date,
                inco_terms          = row.get("inco_terms"),
                inco_location       = row.get("inco_location"),
                so_status           = row.get("status"),
            )

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE: Sync first SO's master fields onto the LCRequest header
    # ─────────────────────────────────────────────────────────────────────────

    def _sync_header_from_first_so(self, lc_instance: LCRequest, so_list: list) -> None:
        """
        Denormalise the first SO's master snapshot onto the ``LCRequest``
        header row for fast list-screen reads (avoids a JOIN every page load).

        Args:
            lc_instance: The parent ``LCRequest`` to update in-place.
            so_list:     Parsed list of SO dicts from the frontend payload.
        """
        if not so_list:
            return

        first = so_list[0]
        lc_instance.company_code       = first.get("company_code")
        lc_instance.plant_code         = first.get("plant_code")
        lc_instance.customer_code      = first.get("customer_code")
        lc_instance.ship_to_party      = first.get("ship_to_party")
        lc_instance.so_value           = first.get("so_value")
        lc_instance.payment_terms      = first.get("pyt_terms")
        lc_instance.special_remark     = first.get("remarks")
        lc_instance.cust_ref_po_number = first.get("cust_reference")
        lc_instance.cust_ref_po_date   = first.get("cust_reference_date") or None
        lc_instance.save()

    # ─────────────────────────────────────────────────────────────────────────
    # OCR — extract PDF data, persist draft, return OCR response + lc_id
    # ─────────────────────────────────────────────────────────────────────────

    def extract_and_save(self, request) -> Response:
        """
        1. Proxy PDF to external OCR engine.
        2. Map prediction → ``LCRequest`` fields, persist as a draft inside a
           reversion revision (Version 1 = raw OCR output).
        3. Return full OCR payload + ``lc_id`` so the frontend switches
           subsequent saves from POST (create) → PATCH (update same draft).

        Args:
            request: DRF ``Request`` with ``FILES["file"]``.
        """
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response(
                {"error": "No file uploaded. Send the PDF as 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 1. Forward PDF to OCR engine ──────────────────────────────────────
        try:
            ocr_response = requests.post(
                _OCR_URL,
                files={"file": (
                    uploaded_file.name,
                    uploaded_file.read(),
                    uploaded_file.content_type,
                )},
                data={"project_name": _OCR_PROJECT_NAME},
                timeout=_OCR_TIMEOUT_SECS,
                verify=False,   # internal staging cert — remove in production
            )
        except requests.exceptions.Timeout:
            return Response(
                {"error": "OCR API timed out. Please try again."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            logger.error("OCR API unreachable: %s", exc)
            return Response(
                {"error": f"Could not reach OCR API: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            ocr_data = ocr_response.json()
        except ValueError:
            return Response(
                {"error": "OCR API returned a non-JSON response."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── 2. Persist draft LCRequest ────────────────────────────────────────
        prediction    = ocr_data.get("prediction", {})
        mapped_fields = self._map_ocr_prediction(prediction)

        uploaded_file.seek(0)   # rewind — .read() moved the pointer to EOF

        with reversion.create_revision():
            lc_instance = LCRequest.objects.create(
                status     = "draft",
                attachment = uploaded_file,
                **mapped_fields,
            )
            reversion.set_comment("Version 1 — original OCR extraction")

        logger.info("OCR draft created: LCRequest pk=%s", lc_instance.pk)

        # ── 3. Return OCR payload + lc_id ─────────────────────────────────────
        return Response(
            {**ocr_data, "lc_id": lc_instance.pk},
            status=ocr_response.status_code,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # GET LIST
    # ─────────────────────────────────────────────────────────────────────────

    def get_lc_list(self, query_params) -> Response:
        """Paginated LC Request list with optional search and status filter."""
        queryset = LCRequest.objects.all().order_by("-created_date")

        search = query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(customer_code__icontains=search)
                | Q(instrument_number__icontains=search)
                | Q(status__icontains=search)
                | Q(company_code__icontains=search)
            )

        if query_params.get("filter"):
            filter_status = query_params.get("status")
            if filter_status:
                queryset = queryset.filter(status=filter_status)

        page_size = int(query_params.get("pageSize", 20))
        page_no   = int(query_params.get("page", 1))
        paginator = Paginator(queryset, page_size)
        page_obj  = paginator.get_page(page_no)

        serializer = LCRequestSerializer(page_obj.object_list, many=True)
        return Response({"total": paginator.count, "results": serializer.data})

    # ─────────────────────────────────────────────────────────────────────────
    # GET SINGLE
    # ─────────────────────────────────────────────────────────────────────────

    def get_lc_by_id(self, pk: int) -> Response:
        """
        Returns full LC Request detail including nested SO rows.

        ``prefetch_related("so_details__lc_so_detail")`` fetches all
        ``SODetail`` rows and their linked ``LCSODetail`` in two extra queries
        instead of N+1 — important when many SOs are attached to one LC.
        """
        try:
            instance = (
                LCRequest.objects
                .prefetch_related("so_details__lc_so_detail")
                .get(pk=pk)
            )
        except LCRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(LCRequestSerializer(instance).data)

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE  (POST)
    # ─────────────────────────────────────────────────────────────────────────

    def create_lc_request(self, request) -> Response:
        """Create a new ``LCRequest`` and record Version 1 in reversion."""
        data       = request.data
        serializer = LCRequestWriteSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with reversion.create_revision():
            lc_instance = serializer.save()

            so_details_raw = data.get("so_details")
            if so_details_raw:
                try:
                    so_list = json.loads(so_details_raw)
                    self._sync_header_from_first_so(lc_instance, so_list)
                except (json.JSONDecodeError, TypeError):
                    pass
                self._save_so_details(lc_instance, so_details_raw)

            reversion.set_user(request.user)
            reversion.set_comment("Version 1 — initial manual save")

        return Response(
            LCRequestSerializer(lc_instance).data,
            status=status.HTTP_201_CREATED,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE  (PATCH)
    # ─────────────────────────────────────────────────────────────────────────

    def update_lc_request(self, request, pk: int) -> Response:
        """
        Partial update — only fields in ``request.data`` are changed.
        Creates a new reversion ``Version`` so every edit is tracked.
        """
        data = request.data

        try:
            instance = LCRequest.objects.get(pk=pk)
        except LCRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = LCRequestWriteSerializer(instance, data=data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with reversion.create_revision():
            lc_instance = serializer.save()

            so_details_raw = data.get("so_details")
            if so_details_raw:
                try:
                    so_list = json.loads(so_details_raw)
                    self._sync_header_from_first_so(lc_instance, so_list)
                except (json.JSONDecodeError, TypeError):
                    pass
                self._save_so_details(lc_instance, so_details_raw)

            reversion.set_user(request.user)
            reversion.set_comment(
                f"Updated by {request.user} — status: {data.get('status', instance.status)}"
            )

        return Response(LCRequestSerializer(lc_instance).data)

    # ─────────────────────────────────────────────────────────────────────────
    # VERSION HISTORY
    # ─────────────────────────────────────────────────────────────────────────

    def get_version_history(self, pk: int) -> Response:
        """Returns all saved versions of an ``LCRequest``, newest first."""
        try:
            instance = LCRequest.objects.get(pk=pk)
        except LCRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        versions = (
            Version.objects
            .get_for_object(instance)
            .select_related("revision__user")
        )

        history = [
            {
                "version_id":   v.pk,
                "revision_id":  v.revision.pk,
                "date_created": v.revision.date_created,
                "user":         str(v.revision.user) if v.revision.user else "system",
                "comment":      v.revision.comment or "",
                "field_dict":   v.field_dict,
            }
            for v in versions
        ]

        return Response(history)

    # ─────────────────────────────────────────────────────────────────────────
    # SO LOOKUP — proxy to Masters API
    # ─────────────────────────────────────────────────────────────────────────

    def get_so_details(self, request, so_number: str) -> Response:
        """
        Forward an SO lookup to the Masters service and return its response.

        Args:
            request:   DRF ``Request`` (used for scheme/host and auth header).
            so_number: SO number string to look up.
        """
        if not so_number:
            return Response(
                {"error": "so_number is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        prefix       = getattr(settings, "PROJECT_API_PREFIX",      "testproject")
        master_route = getattr(settings, "MASTERS_ROUTE",            "master")
        app_model    = getattr(settings, "MASTERS_SODATA_APP_MODEL", "Master.Sodata")

        base = f"{request.scheme}://{request.get_host()}"
        qs   = urlencode({
            "page":      1,
            "pageSize":  20,
            "so_number": so_number,
            "filter":    1,
        })
        url = f"{base}/{prefix}/{master_route}/{app_model}/list?{qs}"

        headers = {
            "Authorization": request.META.get("HTTP_AUTHORIZATION", ""),
            "Accept":        "application/json",
            "source":        "workflow",
            "req":           "list",
        }

        try:
            r    = requests.get(url, headers=headers, timeout=15)
            data = r.json()
            return Response(data, status=r.status_code)
        except Exception as exc:
            logger.error("Masters API error for SO %s: %s", so_number, exc)
            return Response(
                {"error": f"Upstream error: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )