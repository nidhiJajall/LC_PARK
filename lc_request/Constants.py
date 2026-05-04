"""
App-level constants for the lc_request module.

All runtime secrets (SAP credentials, OCR URL) are read from my_secrets.secrets
so nothing sensitive is committed to source control.
"""
from my_secrets import secrets

APP_LABEL = 'lc_request'

# ── File categories ───────────────────────────────────────────────────────────
LC_DOCUMENT   = 'LC_DOCUMENT'
LC_ATTACHMENT = 'LC_ATTACHMENT'
FILE_CATEGORIES = [LC_DOCUMENT, LC_ATTACHMENT]

# ── Request statuses ──────────────────────────────────────────────────────────
STATUS_DRAFT     = 'draft'
STATUS_SUBMITTED = 'submitted'
STATUS_SYNCED    = 'synced'

STATUS_CHOICES = [
    (STATUS_DRAFT,     'Draft'),
    (STATUS_SUBMITTED, 'Submitted'),
    (STATUS_SYNCED,    'Synced'),
]

# ── OCR API ───────────────────────────────────────────────────────────────────
OCR_URL          = secrets.LC_OCR_URL
OCR_PROJECT_NAME = secrets.LC_OCR_PROJECT_NAME
OCR_TIMEOUT_SECS = int(secrets.LC_OCR_TIMEOUT_SECS)

# Maps raw OCR response key → LcDetails model field name (single source of truth).
# services.py and sap_services.py both import from here — do NOT duplicate this map.
OCR_FIELD_MAP: dict[str, str] = {
    "Instrument_Number":          "instrument_number",
    "Form_of_DOC":                "form_of_doc",
    "Opening_Bank":               "opening_bank",
    "Opening_Date":               "opening_date",
    "Unance_Period":              "unance_period",    # OCR typo preserved intentionally
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

# Extended map: also accepts already-normalised model field names as keys.
# Used by services._extract_lc_detail_fields() for both OCR payloads and
# direct frontend PATCH requests (which send model field names, not OCR keys).
FULL_FIELD_MAP: dict[str, str] = {
    **OCR_FIELD_MAP,
    # model field name aliases (pass-through)
    **{v: v for v in OCR_FIELD_MAP.values()},
    # legacy / alternate spellings seen in frontend payloads
    "usance_period": "unance_period",
}

# Fields that must be coerced to bool ("yes"/"no" → True/False)
OCR_BOOL_FIELDS: frozenset = frozenset({"es", "et", "er"})

# Fields that must be coerced to date (format: DD.MM.YYYY)
OCR_DATE_FIELDS: frozenset = frozenset(
    {"opening_date", "dispatch_upto_date", "expiry_date"}
)

# All editable LC detail field names (used for extracted_flag comparison)
LC_DETAIL_FIELDS: list[str] = list(OCR_FIELD_MAP.values())

# ── Allowed file types ────────────────────────────────────────────────────────
ALLOWED_FILE_EXTENSIONS = ['application/pdf']

# ── SAP OData credentials ─────────────────────────────────────────────────────
SAP_BASE_URL = secrets.SAP_BASE_URL
SAP_CLIENT   = secrets.SAP_CLIENT
SAP_USER     = secrets.SAP_USER
SAP_PASSWORD = secrets.SAP_PASSWORD

SAP_LC_URL = (
    f"{SAP_BASE_URL}/sap/opu/odata/sap/"
    f"ZFI_DOMESTIC_LC_REPLICATION_SRV/"
    f"ZFI_DOMESTIC_LC_POSTSet"
    f"?sap-client={SAP_CLIENT}"
)