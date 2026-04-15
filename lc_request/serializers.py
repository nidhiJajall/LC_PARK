# lc_request/serializers.py
# ─────────────────────────────────────────────────────────────────────────────
# WHY two separate serializers (Read vs Write)?
# ─────────────────────────────────────────────────────────────────────────────
# Read  (LCRequestSerializer)      — used on GET responses.
#   • Includes nested so_details (list of SODetail rows, each with flattened
#     financial fields from the related LCSODetail).
#   • Includes computed/auto fields like created_date, updated_date.
#
# Write (LCRequestWriteSerializer) — used on POST / PATCH.
#   • Excludes so_details (handled separately in services._save_so_details).
#   • Excludes id, created_date, updated_date (auto-set by Django).
#
# WHY does SODetailSerializer flatten LCSODetail financial fields?
#   The frontend expects one flat dict per SO row.  Using DRF's ``source``
#   kwarg on field declarations pulls through-relation values into the
#   top-level response without adding a nested key.
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers

from .models import LCRequest, LCSODetail, SODetail


# ── Shared field lists ────────────────────────────────────────────────────────

LC_DETAIL_FIELDS: list[str] = [
    "instrument_number",
    "form_of_doc",
    "opening_bank",
    "opening_date",
    "usance_period",
    "dispatch_upto_date",
    "negotiation_days",
    "expiry_date",
    "place_take_in_charge",
    "place_of_final_destination",
    "advising_bank",
    "es",
    "et",
    "er",
    "grace_value",
    "percentage_credit_amount_tolerance",
    "cust_name_inv_print",
    "customer_name",
    "clause_45a",
    "incoterm",
    "imps_remark",
    "additional_condition_46a",
    "clause_78",
]

# Fields returned per SO row in GET responses.
# The three financial fields (last three) live on LCSODetail; they are pulled
# in via ``source`` in SODetailSerializer — see below.
SO_DETAIL_FIELDS: list[str] = [
    "id",
    "so_number",
    "company_code",
    "plant_code",
    "customer_code",
    "ship_to_party",
    "so_value",
    "pyt_terms",
    "remarks",
    "cust_reference",
    "cust_reference_date",
    "inco_terms",
    "inco_location",
    "so_status",
    # Financial fields — flattened from the related LCSODetail via source=
    "interest_free_credit_days",
    "interest_charges",
    "usance_period",
]


class SODetailSerializer(serializers.ModelSerializer):
    """
    READ serializer for ``SODetail``.

    Serialises ``SODetail`` rows (the Masters snapshot) and pulls the three
    financial fields from the linked ``LCSODetail`` record via ``source``.

    WHY flatten instead of nesting?
      A nested serializer would produce::

          { "lc_so_detail": { "interest_charges": 1000 } }

      The frontend's SO table renders a flat row — it doesn't need to unwrap
      a sub-object.  Using ``source="lc_so_detail.<field>"`` merges those
      values into the top-level dict automatically.
    """

    # Financial fields pulled through the lc_so_detail OneToOne
    interest_free_credit_days = serializers.IntegerField(
        source   = "lc_so_detail.interest_free_credit_days",
        allow_null = True,
        required   = False,
    )
    interest_charges = serializers.DecimalField(
        source        = "lc_so_detail.interest_charges",
        max_digits    = 10,
        decimal_places = 2,
        allow_null    = True,
        required      = False,
    )
    usance_period = serializers.IntegerField(
        source   = "lc_so_detail.usance_period",
        allow_null = True,
        required   = False,
    )

    class Meta:
        model  = SODetail
        fields = SO_DETAIL_FIELDS


# Alias — keeps any existing ``from .serializers import LCSODetailSerializer``
# imports working without changes in other modules.
LCSODetailSerializer = SODetailSerializer


class LCRequestSerializer(serializers.ModelSerializer):
    """READ serializer — returned by all GET endpoints."""

    so_details = SODetailSerializer(many=True, read_only=True)

    class Meta:
        model  = LCRequest
        fields = [
            "id",
            # SO header snapshot (from first SO, denormalised)
            "company_code",
            "plant_code",
            "customer_code",
            "ship_to_party",
            "so_value",
            "payment_terms",
            "special_remark",
            "cust_ref_po_number",
            "cust_ref_po_date",
            # Attachment
            "attachment",
            "password",
            # 23 LC Detail fields
            *LC_DETAIL_FIELDS,
            # Status + audit
            "status",
            "created_by",
            "created_date",
            "updated_date",
            # Child SO rows
            "so_details",
        ]
        read_only_fields = ["id", "created_date", "updated_date"]


class LCRequestWriteSerializer(serializers.ModelSerializer):
    """
    WRITE serializer — used on POST and PATCH.
    ``so_details`` is excluded; handled in services._save_so_details().
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
            *LC_DETAIL_FIELDS,
            "status",
            "created_by",
        ]


class VersionSummarySerializer(serializers.Serializer):
    """Lightweight shape returned by GET /lc_request/<id>/history/."""

    version_id   = serializers.IntegerField()
    revision_id  = serializers.IntegerField()
    date_created = serializers.DateTimeField()
    user         = serializers.CharField()
    comment      = serializers.CharField()
    field_dict   = serializers.DictField()