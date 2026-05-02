"""
sap_services.py
───────────────
Handles building the SAP LC payload and posting it via the two-step
CSRF-token fetch → POST flow required by SAP OData services.

Flow
────
1.  GET  SAP_LC_URL  with header  x-csrf-token: Fetch
        → response header  x-csrf-token  contains the real token

2.  POST SAP_LC_URL  with that token in  x-csrf-token  header
        → SAP creates the LC record

On success the SAP response contains a Return string such as:
    "Inward number 1100029908 created successfully against LC number 4000855"

`post_lc_to_sap` extracts both numbers and persists them alongside
a status change to Constants.STATUS_SYNCED on the LcRequest row.

Authentication: HTTP Basic  (SAP_USER / SAP_PASSWORD from Constants)
"""

import logging
import re
from collections import defaultdict
from datetime import date, datetime

import requests
from requests.auth import HTTPBasicAuth

from lc_request import Constants
from lc_request.models import LcRequest

logger = logging.getLogger(__name__)

# ── SAP auth (single source of truth from Constants) ─────────────────────────
_SAP_AUTH = HTTPBasicAuth(Constants.SAP_USER, Constants.SAP_PASSWORD)

# Regex to extract numbers from the SAP return message.
# Matches: "Inward number 1100029908 created successfully against LC number 4000855"
_SAP_RETURN_RE = re.compile(
    r"Inward number\s+(\S+).*?LC number\s+(\S+)",
    re.IGNORECASE,
)


# ── Shared session so cookies are retained between the GET and POST ───────────
def _make_session() -> requests.Session:
    s = requests.Session()
    s.auth = _SAP_AUTH
    s.verify = False          # SAP cert is self-signed in staging
    s.headers.update({
        "Accept":       "application/json",
        "Content-Type": "application/json",
    })
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_sap_date(val) -> str:
    """
    Convert a Python date/datetime or ISO string to SAP's OData JSON date
    format:  /Date(<milliseconds>)/
    Returns empty string for null / invalid values.
    """
    if not val:
        return ""
    if isinstance(val, (date, datetime)):
        dt = datetime(val.year, val.month, val.day)
    elif isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(val, fmt)
                break
            except ValueError:
                continue
        else:
            return ""
    else:
        return ""

    ms = int(dt.timestamp() * 1000)
    return f"/Date({ms})/"


def _incoterm_freight(incoterm: str) -> str:
    """
    Mapping: pre-paid incoterms → "PRE-PAID", others → "TO-PAY".
    Matches the logic in the intern's migration script and the mapping sheet.
    """
    if not incoterm:
        return "TO-PAY"
    prepaid = {"CFR", "CIF", "CPT", "CIP", "DAP", "DAT", "DDP", "DPU"}
    # Incoterm field may be "CIF HAMBURG" — take just the first word
    code = incoterm.strip().split()[0].upper()
    return "PRE-PAID" if code in prepaid else "TO-PAY"


def _split_text_to_notes(text: str, chunk_chars: int, num_chunks: int) -> list:
    """
    Split a long text into fixed-character chunks for SAP NOTE fields.
    Returns a list of exactly num_chunks strings (empty string for unused slots).
    """
    text = (text or "").replace("\n", " ")
    # Collapse multiple spaces
    text = " ".join(text.split())
    chunks = []
    for i in range(num_chunks):
        start = i * chunk_chars
        chunk = text[start: start + chunk_chars].strip()
        chunks.append(chunk)
    return chunks


def _parse_tolerance(raw: str):
    """
    Parse 'percentage_credit_amount_tolerance' value.
    Accepted formats: "10/10", "05/02", "10", "5".
    Returns (grace_qty_pct, grace_val_pct) as strings — SAP expects strings.
    """
    if not raw:
        return "0", "0"
    raw = str(raw).strip()
    if "/" in raw:
        parts = raw.split("/", 1)
        try:
            return str(int(float(parts[0]))), str(int(float(parts[1])))
        except ValueError:
            return "0", "0"
    try:
        v = str(int(float(raw)))
        return v, v
    except ValueError:
        return "0", "0"


def _fmt_decimal(val, decimal_places: int = 2) -> str:
    """
    Format a numeric value as a fixed-decimal string for SAP.
    SAP OData XML parser requires all numeric values to be JSON strings.
    Examples: Decimal('60164501') -> '60164501.00',  None -> '0.00'
    """
    if val is None or val == "":
        return f"0.{'0' * decimal_places}"
    try:
        from decimal import Decimal as D
        return f"{D(str(val)):.{decimal_places}f}"
    except Exception:
        return f"0.{'0' * decimal_places}"


def _fmt_int(val) -> str:
    """Format an integer-like value as a plain string. None -> '0'."""
    if val is None or val == "":
        return "0"
    try:
        return str(int(val))
    except Exception:
        return "0"


def _parse_sap_return(sap_body: dict) -> tuple[str | None, str | None]:
    """
    Extract (inward_no, lc_ref_no) from the SAP response body.

    SAP wraps the result in:
        sap_body["d"]["to_results"]["Return"]
            → "Inward number 1100029908 created successfully against LC number 4000855"

    Returns (None, None) if the message is absent or doesn't match.
    """
    try:
        return_msg = sap_body["d"]["to_results"]["Return"]
    except (KeyError, TypeError):
        logger.warning("SAP response missing d.to_results.Return — cannot extract numbers")
        return None, None

    match = _SAP_RETURN_RE.search(str(return_msg))
    if not match:
        logger.warning("SAP Return message did not match expected pattern: %r", return_msg)
        return None, None

    inward_no = match.group(1).rstrip(".,;")   # strip any trailing punctuation
    lc_ref_no = match.group(2).rstrip(".,;")
    return inward_no, lc_ref_no


# ─────────────────────────────────────────────────────────────────────────────
# Payload builder  (pure function — no I/O)
# ─────────────────────────────────────────────────────────────────────────────

def build_lc_payload(lc_request: LcRequest) -> dict:
    """
    Build the complete SAP OData POST body for a single LcRequest.

    Data sources (priority order per the mapping sheet):
        OCR  → TRANS_LC_DETAILS  (lc_request.lc_details)
        User → TRANS_LC_REQUEST  (lc_request itself)
        SO   → MST_SODATA        (lc_request.so_data M2M)

    Returns a plain dict ready for json.dumps / requests.post(json=...).
    """
    det = lc_request.lc_details       # LcDetails (N entry — user editable)
    so_list = list(lc_request.so_data.all())
    first_so = so_list[0] if so_list else None

    # ── BUKRS / KUNNR from first SO ──────────────────────────────────────────
    company_code = (first_so.company_code if first_so else "") or "2000"
    customer_code = (first_so.customer_code if first_so else "") or ""

    # ── Grace / tolerance ────────────────────────────────────────────────────
    grace_qty, grace_val = _parse_tolerance(
        det.percentage_credit_amount_tolerance if det else None
    )

    # ── Transport mode flags (ES / ET / ER) ──────────────────────────────────
    def _is_active(flag_val) -> bool:
        if flag_val is None:
            return False
        if isinstance(flag_val, bool):
            return flag_val
        return str(flag_val).lower() == "yes"

    vsart_flags = []
    if det:
        if _is_active(det.es):
            vsart_flags.append("ES")
        if _is_active(det.et):
            vsart_flags.append("ET")
        if _is_active(det.er):
            vsart_flags.append("ER")

    # Pad / trim to exactly 4 VSART slots
    vsart_values = (vsart_flags + ["", "", "", ""])[:4]

    # ── Ship-to parties (up to 4 unique values from SO list) ─────────────────
    seen_ship = []
    for so in so_list:
        if so.ship_to_party and so.ship_to_party not in seen_ship:
            seen_ship.append(so.ship_to_party)
        if len(seen_ship) == 4:
            break
    ship_parties = (seen_ship + ["", "", "", ""])[:4]

    # ── WERKS from first SO ──────────────────────────────────────────────────
    werks = (first_so.plant_code if first_so else "") or ""

    # ── PURORDERs — one per SO (up to 24) ───────────────────────────────────
    purorders = ([so.so_number or "" for so in so_list] + [""] * 24)[:24]

    # ── NOTE fields ──────────────────────────────────────────────────────────
    # NOTE1–2 : Customer name for invoice print (35 chars each)
    cust_inv = (det.cust_name_inv_print if det else "") or ""
    note1_2 = _split_text_to_notes(cust_inv, 35, 2)

    # NOTE2 override: full customer name if available
    customer_name = (det.customer_name if det else "") or ""
    note2_val = customer_name[:35] if customer_name else note1_2[1]

    # NOTE3–5 : Advising bank address (35 chars each, 3 slots)
    adv_bank_addr = (det.advising_bank if det else "") or ""
    note3_5 = _split_text_to_notes(adv_bank_addr, 35, 3)

    # NOTE9–11, NOTE13–15 : Additional conditions 46A (35 chars, 6 slots)
    add_cond = (det.additional_condition_46a if det else "") or ""
    note10_15 = _split_text_to_notes(add_cond, 35, 6)

    # NOTE12 : Incoterm location (clause 78)
    clause78 = (det.clause_78 if det else "") or ""
    note12_val = clause78[:35]

    # ── Line items ───────────────────────────────────────────────────────────
    to_items = []
    for so in so_list:
        if hasattr(so, 'items') and so.items.exists():
            for row in so.items.all():
                to_items.append({
                    "VBELN":     so.so_number or "",
                    "POSNR":     str(row.line_item or "000010"),
                    "INSMATNO":  str(row.material_no or ""),
                    "MATLPRICE": _fmt_decimal(row.material_price),
                    "INSQUAN":   _fmt_decimal(row.material_qty),
                    "INSVAL":   "1",
                    "INSQUANU":  str(row.unit or ""),
                })
        else:
            # Fallback: one skeleton row per SO so SAP always gets a line
            to_items.append({
                "VBELN":     so.so_number or "",
                "POSNR":     "000010",
                "INSMATNO":  "",
                "MATLPRICE": "0.00",
                "INSQUAN":   "0",
                "INSVAL":    "0.00",
                "INSQUANU":  "",
            })

    # ── Assemble header ──────────────────────────────────────────────────────
    incoterm_str = (det.incoterm if det else "") or ""

    payload = {
        # [1–4] Core identifiers
        "BUKRS":    company_code,
        "KUNNR":    customer_code,
        "INSFACENR": (det.instrument_number if det else "") or "",
        "INSGENNR": "",                           # Inward number — always null per mapping

        # [5–8] Value & currency — must be strings (SAP XML parser rejects JSON numbers)
        "INSCURR":  "INR",                        # constant
        "FACEVAL":  _fmt_decimal(det.grace_value if det else None),
        "EXCHRATE": "1",                          # constant
        "FACEVLIR": _fmt_decimal(det.grace_value if det else None),

        # [9–10] Key dates
        "OPENDATE": _fmt_sap_date(det.opening_date if det else None),
        "EXPYDATE": _fmt_sap_date(det.expiry_date if det else None),

        # [11–12] Grace / tolerance
        "GRACEPERQ": grace_qty,
        "GRACEPERV": grace_val,

        # [13–14] Opening bank (constant country code IN)
        "OPNBKC":  "IN",                          # constant
        "OPNBANK": (det.opening_bank if det else "") or "",

        # [15–19] Dispatch / negotiation / advising / incoterm
        "DESPDATE": _fmt_sap_date(det.dispatch_upto_date if det else None),
        "NEGOPER":  _fmt_int(det.negotiation_days if det else None),
        "ADVBANK":  (det.advising_bank if det else "") or "",
        "INCOIND":  incoterm_str,
        "RECVDATE": _fmt_sap_date(det.opening_date if det else None),   # same as opening date per mapping

        "GFADDATE": "/Date(0)/",
        "RAADDATE": "/Date(0)/",

        # [20–22] Null dates + status
        "STATUS":   "2",                          # constant

        # [23] Negotiation upto date = expiry date per mapping
        "NEGODATE": _fmt_sap_date(det.expiry_date if det else None),

        # [24–27] Transport mode flags
        "VSART1": vsart_values[0],
        "VSART2": vsart_values[1],
        "VSART3": vsart_values[2],
        "VSART4": vsart_values[3],

        # [28] Freight payment indicator
        "FRTPYIND": _incoterm_freight(incoterm_str),

        # [29–32] Ship-to parties
        "SHPPARTY1": ship_parties[0],
        "SHPPARTY2": ship_parties[1],
        "SHPPARTY3": ship_parties[2],
        "SHPPARTY4": ship_parties[3],

        # [33–35] Plant / payment method
        "WERKS":   werks,
        "PAYMETH": "O",                           # constant per mapping

        # [36–59] PURORDERs 1–24 (SO numbers)
        **{f"PURORDER{i+1}": purorders[i] for i in range(24)},

        # [60–65] Boolean indicators — all TRUE per mapping
        "STOPIND":  "X",
        "MATRIND":  "X",
        "PDISIND":  "X",
        "INTRIND":  "X",
        "POIND":    "X",
        "PRICEIND": "X",

        # [66–68] Advising / negotiating bank country codes
        "ADVBKC":  "IN",                          # constant
        "NEGBKC":  "IN",                          # constant
        "NEGBANK": (det.advising_bank if det else "") or "",  # presenting bank = advising bank

        # [69–71] User-entered financial fields
        "INTFREDY": _fmt_int(lc_request.interest_free_credit_days),
        "INTRATE":  _fmt_decimal(lc_request.interest_charges),
        "USANCEPER": _fmt_int(lc_request.usance_period),

        # [72] Insurance value header — constant
        "INSVALUE": "1",

        # [73–87] NOTE fields
        "NOTE1":  note1_2[0],
        "NOTE2":  note2_val,
        "NOTE3":  note3_5[0],
        "NOTE4":  note3_5[1],
        "NOTE5":  note3_5[2],
        "NOTE6":  "",
        "NOTE7":  "",
        "NOTE8":  "",
        "NOTE9":  note10_15[0],
        "NOTE10": note10_15[1],
        "NOTE11": note10_15[2],
        "NOTE12": note12_val,
        "NOTE13": note10_15[3],
        "NOTE14": note10_15[4],
        "NOTE15": note10_15[5],

        # [88] Line items
        "to_items": to_items,

        # [89] Return navigation property — must be an empty list for SAP OData v2;
        #      sending a dict here causes a 500 "unknown internal server error" in SAP.
        "to_results": {"Return": ""},
    }

    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Two-step SAP post  (GET csrf → POST data)
# ─────────────────────────────────────────────────────────────────────────────

def post_lc_to_sap(lc_request: LcRequest) -> dict:
    """
    Execute the two-step SAP OData create flow:

    Step 1  GET  SAP_LC_URL   header: x-csrf-token = Fetch
    Step 2  POST SAP_LC_URL   header: x-csrf-token = <token from step 1>
                               body: build_lc_payload(lc_request)

    On success:
      - Parses the SAP Return message to extract inward_no and lc_ref_no.
      - Saves both values + flips request_status to Constants.STATUS_SYNCED
        on the LcRequest row.

    Returns a dict:
        {
            "success":      bool,
            "status_code":  int,
            "sap_response": dict | str,    # parsed JSON or raw text
            "payload":      dict,          # the payload that was sent
        }
    """
    session = _make_session()
    payload = build_lc_payload(lc_request)

    # ── Step 1: fetch CSRF token ──────────────────────────────────────────────
    try:
        csrf_resp = session.get(
            Constants.SAP_LC_URL,
            headers={"x-csrf-token": "Fetch"},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("SAP CSRF fetch failed: %s", exc)
        return {
            "success": False,
            "status_code": 503,
            "sap_response": f"SAP unreachable during CSRF fetch: {exc}",
            "payload": payload,
        }

    csrf_token = csrf_resp.headers.get("x-csrf-token") or csrf_resp.headers.get("X-CSRF-Token")
    if not csrf_token:
        logger.error(
            "SAP CSRF token missing in response. Status %s. Headers: %s",
            csrf_resp.status_code, dict(csrf_resp.headers)
        )
        return {
            "success": False,
            "status_code": csrf_resp.status_code,
            "sap_response": "No x-csrf-token returned by SAP",
            "payload": payload,
        }

    logger.info("SAP CSRF token acquired (status %s)", csrf_resp.status_code)

    # ── Step 2: POST the payload ──────────────────────────────────────────────
    try:
        post_resp = session.post(
            Constants.SAP_LC_URL,
            json=payload,
            headers={"x-csrf-token": csrf_token},
            timeout=60,
        )
    except requests.RequestException as exc:
        logger.error("SAP POST failed: %s", exc)
        return {
            "success": False,
            "status_code": 503,
            "sap_response": f"SAP unreachable during POST: {exc}",
            "payload": payload,
        }

    try:
        sap_body = post_resp.json()
    except ValueError:
        sap_body = post_resp.text

    success = post_resp.status_code in (200, 201)

    if success:
        logger.info("SAP LC POST succeeded (status %s)", post_resp.status_code)

        # ── Parse Return message & persist on LcRequest ───────────────────────
        inward_no, lc_ref_no = _parse_sap_return(sap_body if isinstance(sap_body, dict) else {})

        update_fields = ["request_status"]
        lc_request.request_status = Constants.STATUS_SYNCED

        if inward_no:
            lc_request.inward_no = inward_no
            update_fields.append("inward_no")
            logger.info("Saving inward_no=%s for LcRequest #%s", inward_no, lc_request.pk)

        if lc_ref_no:
            lc_request.lc_ref_no = lc_ref_no
            update_fields.append("lc_ref_no")
            logger.info("Saving lc_ref_no=%s for LcRequest #%s", lc_ref_no, lc_request.pk)

        lc_request.save(update_fields=update_fields)

    else:
        logger.error(
            "SAP LC POST failed (status %s): %s",
            post_resp.status_code, sap_body,
        )

    return {
        "success": success,
        "status_code": post_resp.status_code,
        "sap_response": sap_body,
        "payload": payload,
    }