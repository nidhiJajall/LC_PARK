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

_INT_FIELDS = frozenset({"unance_period", "negotiation_days"})
_DECIMAL_FIELDS = frozenset({"grace_value"})

_FIELD_MAP = {
    "Instrument_Number": "instrument_number",
    "instrument_number": "instrument_number",
    "Form_of_DOC": "form_of_doc",
    "form_of_doc": "form_of_doc",
    "Opening_Bank": "opening_bank",
    "opening_bank": "opening_bank",
    "Opening_Date": "opening_date",
    "opening_date": "opening_date",
    "Unance_Period": "unance_period",
    "usance_period": "unance_period",
    "Dispatch_Upto_Date": "dispatch_upto_date",
    "dispatch_upto_date": "dispatch_upto_date",
    "Negotiation_Days": "negotiation_days",
    "negotiation_days": "negotiation_days",
    "Expiry_Date": "expiry_date",
    "expiry_date": "expiry_date",
    "Place_TakeIn_charge": "place_take_in_charge",
    "place_take_in_charge": "place_take_in_charge",
    "Place_of_Final_Destination": "place_of_final_destination",
    "place_of_final_destination": "place_of_final_destination",
    "Advising_Bank": "advising_bank",
    "advising_bank": "advising_bank",
    "ES": "es", "es": "es",
    "ET": "et", "et": "et",
    "ER": "er", "er": "er",
    "Grace_Value": "grace_value",
    "grace_value": "grace_value",
    "Credit_Tolerance": "percentage_credit_amount_tolerance",
    "percentage_credit_amount_tolerance": "percentage_credit_amount_tolerance",
    "Cust_Name_Inv_Print": "cust_name_inv_print",
    "cust_name_inv_print": "cust_name_inv_print",
    "Customer_Name": "customer_name",
    "customer_name": "customer_name",
    "Clause_45A": "clause_45a",
    "clause_45a": "clause_45a",
    "Incoterm": "incoterm",
    "incoterm": "incoterm",
    "IMPS Remark": "imps_remark",
    "imps_remark": "imps_remark",
    "Additional_Condition_47A": "additional_condition_46a",
    "additional_condition_46a": "additional_condition_46a",
    "Clause78": "clause_78",
    "clause_78": "clause_78",
}


class LCRequestService:

    @staticmethod
    def _coerce_int(val):
        if val in (None, "", "Invalid Date", "null", "undefined"):
            return None
        try:
            return int(val)
        except Exception:
            return None

    @staticmethod
    def _coerce_decimal(val):
        if val in (None, "", "Invalid Date", "null", "undefined"):
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    @staticmethod
    def _coerce_date(val):
        if not val or val in ("Invalid Date", "null", "undefined", ""):
            return None
        if isinstance(val, str):
            # OCR format: 31.03.2026
            if '.' in val:
                try:
                    return datetime.strptime(val, "%d.%m.%Y").date()
                except ValueError:
                    pass
            # Frontend format: 2026-03-31
            if '-' in val:
                try:
                    return datetime.strptime(val, "%Y-%m-%d").date()
                except ValueError:
                    pass
        return None

    def _extract_lc_detail_fields(self, data) -> dict:
        result = {}
        for fe_key, model_field in _FIELD_MAP.items():
            raw = data.get(fe_key)
            if raw is None:
                continue

            if model_field in {"opening_date", "dispatch_upto_date", "expiry_date"}:
                result[model_field] = self._coerce_date(raw)
            elif model_field in _INT_FIELDS:
                result[model_field] = self._coerce_int(raw)
            elif model_field in _DECIMAL_FIELDS:
                result[model_field] = self._coerce_decimal(raw)
            else:
                result[model_field] = raw if raw not in ("", "Invalid Date", "null", "undefined") else None
        return result

    @staticmethod
    def _save_so_details(lc_instance: LcRequest, so_details_raw):
        if not so_details_raw:
            return
        try:
            so_list = json.loads(so_details_raw) if isinstance(so_details_raw, str) else so_details_raw
        except Exception:
            return
        if not isinstance(so_list, list):
            return

        from masters.models.Sodata import Sodata
        so_numbers = [row.get("so_number") for row in so_list if row.get("so_number")]
        sodata_qs = Sodata.objects.filter(so_number__in=so_numbers)
        lc_instance.so_data.set(sodata_qs)

    @staticmethod
    def _find_y_entry(n_entry: LcDetails):
        if not n_entry or not n_entry.instrument_number:
            return None
        return LcDetails.objects.filter(
            instrument_number=n_entry.instrument_number,
            extracted_flag='Y'
        ).first()

    # ====================== OCR ======================
    def extract_ocr_data(self, request) -> Response:
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ocr_resp = requests.post(
                Constants.OCR_URL,
                files={"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.content_type)},
                data={"project_name": Constants.OCR_PROJECT_NAME},
                timeout=Constants.OCR_TIMEOUT_SECS,
                verify=False,
            )
            return Response(ocr_resp.json(), status=ocr_resp.status_code)
        except Exception as e:
            logger.error("OCR Error: %s", e)
            return Response({"error": "OCR service unavailable"}, status=status.HTTP_502_BAD_GATEWAY)

    # ====================== CREATE ======================
    def create_lc_request(self, request) -> Response:
        data = request.data
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

        return Response(LCRequestDetailSerializer(lc_instance).data, status=status.HTTP_201_CREATED)

    # ====================== UPDATE ======================
    def update_lc_request(self, request, pk: int) -> Response:
        data = request.data
        files = request.FILES

        try:
            lc_instance = LcRequest.objects.select_related("lc_details").get(pk=pk)
        except LcRequest.DoesNotExist:
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

            reversion.set_comment(f"Updated — status: {lc_instance.request_status}")

        return Response(LCRequestDetailSerializer(lc_instance).data)

    # ====================== LIST ======================
    def get_lc_list(self, query_params):
        qs = LcRequest.objects.prefetch_related("so_data").select_related("lc_details").order_by("-created_date")

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
        page_obj = paginator.get_page(int(query_params.get("page", 1)))

        serializer = LCRequestListSerializer(page_obj.object_list, many=True)
        return Response({"total": paginator.count, "results": serializer.data})

    # ====================== DETAIL ======================
    def get_lc_by_id(self, pk: int):
        try:
            instance = LcRequest.objects.select_related("lc_details").prefetch_related("so_data").get(pk=pk)
            return Response(LCRequestDetailSerializer(instance).data)
        except LcRequest.DoesNotExist:
            return Response({"error": "LC Request not found."}, status=status.HTTP_404_NOT_FOUND)