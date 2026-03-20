# lc_request/serializers.py

from rest_framework import serializers
from .models import LCRequest, LCSODetail


class LCSODetailSerializer(serializers.ModelSerializer):
    """Serializer for each child SO row."""

    class Meta:
        model  = LCSODetail
        fields = [
            "id",
            "so_number",
            "interest_free_credit_days",
            "interest_charges",
            "usance_period",
        ]


class LCRequestSerializer(serializers.ModelSerializer):
    """
    Read serializer — used for GET responses.
    so_details is nested and read-only here.
    """
    so_details = LCSODetailSerializer(many=True, read_only=True)

    class Meta:
        model  = LCRequest
        fields = [
            "id",
            "company_code",
            "plant_code",
            "customer_code",
            "ship_to_party",
            "so_value",
            "payment_terms",
            "special_remark",
            "cust_ref_po_number",
            "cust_ref_po_date",
            "attachment",
            "password",
            "status",
            "created_by",
            "created_date",
            "updated_date",
            "so_details",
        ]
        read_only_fields = ["id", "created_date", "updated_date"]


class LCRequestWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer — used for POST / PATCH.
    so_details is NOT included here because it arrives as a
    raw JSON string from FormData and is handled manually in services.py.
    """

    class Meta:
        model  = LCRequest
        fields = [
            "company_code",
            "plant_code",
            "customer_code",
            "ship_to_party",
            "so_value",
            "payment_terms",
            "special_remark",
            "cust_ref_po_number",
            "cust_ref_po_date",
            "attachment",
            "password",
            "status",
            "created_by",
        ]
