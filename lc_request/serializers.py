from decimal import Decimal
from datetime import date
from rest_framework import serializers

from .models import LcRequest, LcDetails, LcFiles
from masters.models.Sodata import Sodata

LC_DETAIL_FIELDS = [
    "instrument_number", "form_of_doc", "opening_bank", "opening_date", "unance_period",
    "dispatch_upto_date", "negotiation_days", "expiry_date", "place_take_in_charge",
    "place_of_final_destination", "advising_bank", "es", "et", "er", "grace_value",
    "percentage_credit_amount_tolerance", "cust_name_inv_print", "customer_name",
    "clause_45a", "incoterm", "imps_remark", "additional_condition_46a", "clause_78",
]


class LcDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LcDetails
        fields = ["lc_details_id", "extracted_flag"] + LC_DETAIL_FIELDS


class LcFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LcFiles
        fields = ["id", "file", "category", "status", "password", "lc_details"]


class LCRequestListSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='request_status', read_only=True)

    # SO related fields
    so_number = serializers.SerializerMethodField()
    customer_code = serializers.SerializerMethodField()
    so_value = serializers.SerializerMethodField()

    # === OCR Extracted Fields (Flattened) ===
    instrument_number = serializers.SerializerMethodField()
    opening_bank = serializers.SerializerMethodField()
    opening_date = serializers.SerializerMethodField()
    expiry_date = serializers.SerializerMethodField()
    dispatch_upto_date = serializers.SerializerMethodField()
    usance_period = serializers.SerializerMethodField()
    negotiation_days = serializers.SerializerMethodField()
    place_take_in_charge = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    cust_name_inv_print = serializers.SerializerMethodField()
    grace_value = serializers.SerializerMethodField()
    incoterm = serializers.SerializerMethodField()

    class Meta:
        model = LcRequest
        fields = [
            "id", "status", "created_by", "created_date",
            "so_number", "customer_code", "so_value",
            # OCR Fields
            "instrument_number", "opening_bank", "opening_date",
            "expiry_date", "dispatch_upto_date", "usance_period",
            "negotiation_days", "place_take_in_charge", "customer_name",
            "cust_name_inv_print", "grace_value", "incoterm",
            # SAP sync result fields
            "inward_no", "lc_ref_no",
        ]

    def get_so_number(self, obj):
        nums = [s.so_number for s in obj.so_data.all() if s.so_number]
        return ", ".join(nums) if nums else "—"

    def get_customer_code(self, obj):
        so = obj.so_data.first()
        return so.customer_code if so else "—"

    def get_so_value(self, obj):
        from django.db.models import Sum
        agg = obj.so_data.aggregate(total=Sum('so_value'))
        total = agg.get('total')
        return str(total) if total is not None else "0"

    # Flatten LcDetails fields
    def get_instrument_number(self, obj):
        return obj.lc_details.instrument_number if obj.lc_details else None

    def get_opening_bank(self, obj):
        return obj.lc_details.opening_bank if obj.lc_details else None

    def get_opening_date(self, obj):
        return str(obj.lc_details.opening_date) if obj.lc_details and obj.lc_details.opening_date else None

    def get_expiry_date(self, obj):
        return str(obj.lc_details.expiry_date) if obj.lc_details and obj.lc_details.expiry_date else None

    def get_dispatch_upto_date(self, obj):
        return str(obj.lc_details.dispatch_upto_date) if obj.lc_details and obj.lc_details.dispatch_upto_date else None

    def get_usance_period(self, obj):
        return obj.lc_details.unance_period if obj.lc_details else None

    def get_negotiation_days(self, obj):
        return obj.lc_details.negotiation_days if obj.lc_details else None

    def get_place_take_in_charge(self, obj):
        return obj.lc_details.place_take_in_charge if obj.lc_details else None

    def get_customer_name(self, obj):
        return obj.lc_details.customer_name if obj.lc_details else None

    def get_cust_name_inv_print(self, obj):
        return obj.lc_details.cust_name_inv_print if obj.lc_details else None

    def get_grace_value(self, obj):
        return str(obj.lc_details.grace_value) if obj.lc_details and obj.lc_details.grace_value else None

    def get_incoterm(self, obj):
        return obj.lc_details.incoterm if obj.lc_details else None


class LCRequestDetailSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='request_status', read_only=True)
    updated_date = serializers.DateTimeField(source='last_updated_date', read_only=True)
    so_details = serializers.SerializerMethodField()
    attachment = serializers.SerializerMethodField()
    password = serializers.SerializerMethodField()

    class Meta:
        model = LcRequest
        fields = [
            "id", "status", "updated_date",
            "interest_free_credit_days", "interest_charges", "usance_period",
            "created_by", "created_date", "so_details", "attachment", "password",
            # SAP sync result fields — returned to the frontend after a successful sync
            "inward_no", "lc_ref_no",
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.lc_details:
            det = instance.lc_details
            for field in LC_DETAIL_FIELDS:
                val = getattr(det, field, None)
                if isinstance(val, date):
                    rep[field] = str(val)
                elif isinstance(val, Decimal):
                    rep[field] = str(val)
                else:
                    rep[field] = val
            rep["extracted_flag"] = det.extracted_flag
        return rep

    def get_so_details(self, obj):
        return [
            {
                # Primary key & SO identifier
                "id": so.so_id,
                "so_number": so.so_number,

                # Full Sodata (masters) fields — needed by the SODetails table
                "company_code": so.company_code,
                "plant_code": so.plant_code,
                "customer_code": so.customer_code,
                "ship_to_party": so.ship_to_party,
                "ship_to_address": so.ship_to_address,
                "ship_to_city": so.ship_to_city,
                "ship_to_street": so.ship_to_street,
                "ship_to_pincode": so.ship_to_pincode,
                "ship_to_country": so.ship_to_country,
                "so_value": str(so.so_value) if so.so_value is not None else None,
                "pyt_terms": so.pyt_terms,
                "remarks": so.remarks,
                "cust_reference": so.cust_reference,
                "cust_reference_date": str(so.cust_reference_date) if so.cust_reference_date else None,
                "inco_terms": so.inco_terms,
                "inco_location": so.inco_location,
                "status": so.status,

                # LC-level fields
                "interest_free_credit_days": obj.interest_free_credit_days,
                "interest_charges": float(obj.interest_charges) if obj.interest_charges else None,
                "usance_period": obj.usance_period,
            }
            for so in obj.so_data.all()
        ]

    def _get_primary_file(self, obj):
        if not (obj.lc_details and obj.lc_details.instrument_number):
            return None
        y_entry = LcDetails.objects.filter(
            instrument_number=obj.lc_details.instrument_number,
            extracted_flag='Y'
        ).first()
        if not y_entry:
            return None
        return LcFiles.objects.filter(lc_details=y_entry.pk).order_by('id').first()

    def get_attachment(self, obj):
        file_obj = self._get_primary_file(obj)
        return file_obj.file.url if file_obj and file_obj.file else None

    def get_password(self, obj):
        file_obj = self._get_primary_file(obj)
        return file_obj.password if file_obj else None