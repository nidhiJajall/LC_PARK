"""
Module to store LC app-level constants.
"""

APP_LABEL = 'lc_request'

# ── File categories ───────────────────────────────────────────────────────────
LC_DOCUMENT   = 'LC_DOCUMENT'    # The original LC PDF uploaded for OCR
LC_ATTACHMENT = 'LC_ATTACHMENT'  # Any other supporting attachment

FILE_CATEGORIES = [LC_DOCUMENT, LC_ATTACHMENT]

# ── Request statuses ──────────────────────────────────────────────────────────
STATUS_DRAFT     = 'draft'
STATUS_SUBMITTED = 'submitted'
STATUS_SYNCED    = "synced"

STATUS_CHOICES = [
    (STATUS_DRAFT,     'Draft'),
    (STATUS_SUBMITTED, 'Submitted'),
    (STATUS_SYNCED,    'Synced'),
]

# ── OCR API ───────────────────────────────────────────────────────────────────
OCR_URL          = "https://staging.amns.in/bot-ocr/api/v1/extract"
OCR_PROJECT_NAME = "LC PARK & ENTRY"
OCR_TIMEOUT_SECS = 60

# Maps raw OCR response key → LCDetails model field name.
# Single source of truth used by both services and the frontend mapping comment.
OCR_FIELD_MAP: dict[str, str] = {
    "Instrument_Number":          "instrument_number",
    "Form_of_DOC":                "form_of_doc",
    "Opening_Bank":               "opening_bank",
    "Opening_Date":               "opening_date",
    "Unance_Period":              "unance_period",  # OCR typo preserved intentionally
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

# Fields that must be coerced to bool ("yes"/"no" → True/False)
OCR_BOOL_FIELDS: frozenset = frozenset({"es", "et", "er"})

# Fields that must be coerced to date (format: DD.MM.YYYY)
OCR_DATE_FIELDS: frozenset = frozenset(
    {"opening_date", "dispatch_upto_date", "expiry_date"}
)

# All editable LC detail field names (for extracted_flag comparison)
LC_DETAIL_FIELDS: list[str] = list(OCR_FIELD_MAP.values())

# ── Allowed file types ────────────────────────────────────────────────────────
ALLOWED_FILE_EXTENSIONS = [
    'application/pdf'
]

SAP_BASE_URL = "https://vhnmwbadci.sap.myamns.in:44300"
SAP_CLIENT = "150"
SAP_USER = "RFC_AUCTION"
SAP_PASSWORD = "Welcome@987654321"

SAP_LC_URL = (
    f"{SAP_BASE_URL}/sap/opu/odata/sap/"
    f"ZFI_DOMESTIC_LC_REPLICATION_SRV/"
    f"ZFI_DOMESTIC_LC_POSTSet"
    f"?sap-client={SAP_CLIENT}"
)
