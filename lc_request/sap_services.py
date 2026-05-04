"""
SAP LC payload builder and two-step OData POST (CSRF-fetch → POST).

On success, extracts inward_no / lc_ref_no from the SAP return message
and persists them on the LcRequest row with status = STATUS_SYNCED.
Auth: HTTP Basic via SAP_USER / SAP_PASSWORD from Constants.
"""
import logging
import re
from datetime import date, datetime

import requests
from requests.auth import HTTPBasicAuth

from lc_request import Constants
from lc_request.models import LcRequest
from masters.models import Itemdata

logger = logging.getLogger(__name__)

_SAP_AUTH = HTTPBasicAuth(Constants.SAP_USER, Constants.SAP_PASSWORD)

# Matches: "Inward number 1100029908 created successfully against LC number 4000855"
_SAP_RETURN_RE = re.compile(
    r"Inward number\s+(\S+).*?LC number\s+(\S+)",
    re.IGNORECASE,
)


def _make_session() -> requests.Session:
    """Return a pre-configured requests.Session with SAP auth and JSON headers."""
    s = requests.Session()
    s.auth   = _SAP_AUTH
    s.verify = False      # SAP cert is self-signed in staging
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
    return s


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_sap_date(val) -> str:
    """Convert a Python date/str to SAP OData /Date(<ms>)/ format. Returns '' for nulls."""
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
    return f"/Date({int(dt.timestamp() * 1000)})/"


def _incoterm_freight(incoterm: str) -> str:
    """Return 'PRE-PAID' for pre-paid incoterms, otherwise 'TO-PAY'."""
    if not incoterm:
        return "TO-PAY"
    prepaid = {"CFR", "CIF", "CPT", "CIP", "DAP", "DAT", "DDP", "DPU"}
    code    = incoterm.strip().split()[0].upper()
    return "PRE-PAID" if code in prepaid else "TO-PAY"


def _split_text_to_notes(text: str, chunk_chars: int, num_chunks: int) -> list:
    """Split text into fixed-width chunks for SAP NOTE fields. Unused slots are ''."""
    text   = " ".join((text or "").replace("\n", " ").split())
    return [text[i * chunk_chars: (i + 1) * chunk_chars].strip() for i in range(num_chunks)]


def _parse_tolerance(raw: str):
    """Parse '10/10', '05/02', or '10' tolerance strings. Returns (qty_str, val_str)."""
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
    """Format a numeric value as a fixed-decimal string. None → '0.00'."""
    if val is None or val == "":
        return f"0.{'0' * decimal_places}"
    try:
        from decimal import Decimal as D
        return f"{D(str(val)):.{decimal_places}f}"
    except Exception:
        return f"0.{'0' * decimal_places}"


def _fmt_int(val) -> str:
    """Format an integer-like value as a plain string. None → '0'."""
    if val is None or val == "":
        return "0"
    try:
        return str(int(val))
    except Exception:
        return "0"


def _parse_sap_return(sap_body: dict) -> tuple[str | None, str | None]:
    """
    Extract (inward_no, lc_ref_no) from the SAP response body.
    Expects sap_body['d']['to_results']['Return'] to contain the return message.
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

    return match.group(1).rstrip(".,;"), match.group(2).rstrip(".,;")


# ── Payload builder ───────────────────────────────────────────────────────────

def build_lc_payload(lc_request: LcRequest) -> dict:
    """
    Build the complete SAP OData POST body for a single LcRequest.

    Data sources: OCR (lc_request.lc_details), user fields (lc_request),
    and SO master data (lc_request.so_data M2M).
    Returns a plain dict ready for json.dumps / requests.post(json=...).
    """
    det      = lc_request.lc_details
    so_list  = list(lc_request.so_data.all())
    first_so = so_list[0] if so_list else None

    company_code  = (first_so.company_code  if first_so else "") or "2000"
    customer_code = (first_so.customer_code if first_so else "") or ""

    grace_qty, grace_val = _parse_tolerance(
        det.percentage_credit_amount_tolerance if det else None
    )

    def _is_active(flag_val) -> bool:
        if flag_val is None:
            return False
        if isinstance(flag_val, bool):
            return flag_val
        return str(flag_val).lower() == "yes"

    vsart_flags = []
    if det:
        if _is_active(det.es): vsart_flags.append("ES")
        if _is_active(det.et): vsart_flags.append("ET")
        if _is_active(det.er): vsart_flags.append("ER")
    vsart_values = (vsart_flags + ["", "", "", ""])[:4]

    seen_ship = []
    for so in so_list:
        if so.ship_to_party and so.ship_to_party not in seen_ship:
            seen_ship.append(so.ship_to_party)
        if len(seen_ship) == 4:
            break
    ship_parties = (seen_ship + ["", "", "", ""])[:4]

    werks     = (first_so.plant_code if first_so else "") or ""
    purorders = ([so.so_number or "" for so in so_list] + [""] * 24)[:24]

    cust_inv   = (det.cust_name_inv_print if det else "") or ""
    note1_2    = _split_text_to_notes(cust_inv, 35, 2)
    customer_name = (det.customer_name if det else "") or ""
    note2_val  = customer_name[:35] if customer_name else note1_2[1]

    adv_bank_addr = (det.advising_bank if det else "") or ""
    note3_5    = _split_text_to_notes(adv_bank_addr, 35, 3)
    add_cond   = (det.additional_condition_46a if det else "") or ""
    note10_15  = _split_text_to_notes(add_cond, 35, 6)
    clause78   = (det.clause_78 if det else "") or ""
    note12_val = clause78[:35]

    to_items = []

    for so in so_list:
        items = Itemdata.objects.filter(
            so_number=so.so_number,
            status="Active"
        ).order_by("item_number")

        if not items.exists():
            logger.error(
                "No Itemdata found for SO %s — aborting SAP call",
                so.so_number
            )
            raise ValueError(f"No itemdata for SO {so.so_number}")

        for row in items:
            to_items.append({
                "VBELN": so.so_number,
                "POSNR": str(row.item_number).zfill(6),  # SAP format
                "INSMATNO": row.material_no,
                "MATLPRICE": _fmt_decimal(row.material_price),
                "INSQUAN": _fmt_decimal(row.material_qty),
                "INSVAL": "1",
                "INSQUANU": row.unit,
            })

    incoterm_str = (det.incoterm if det else "") or ""

    payload = {
        "BUKRS": company_code,     "KUNNR": customer_code,
        "INSFACENR": (det.instrument_number if det else "") or "",
        "INSGENNR":  "",

        "INSCURR":  "INR",
        "FACEVAL":  _fmt_decimal(det.grace_value if det else None),
        "EXCHRATE": "1",
        "FACEVLIR": _fmt_decimal(det.grace_value if det else None),

        "OPENDATE": _fmt_sap_date(det.opening_date if det else None),
        "EXPYDATE": _fmt_sap_date(det.expiry_date  if det else None),

        "GRACEPERQ": grace_qty,  "GRACEPERV": grace_val,
        "OPNBKC":   "IN",
        "OPNBANK":  (det.opening_bank if det else "") or "",

        "DESPDATE": _fmt_sap_date(det.dispatch_upto_date if det else None),
        "NEGOPER":  _fmt_int(det.negotiation_days if det else None),
        "ADVBANK":  (det.advising_bank if det else "") or "",
        "INCOIND":  incoterm_str,
        "RECVDATE": _fmt_sap_date(det.opening_date if det else None),

        "GFADDATE": "/Date(0)/",  "RAADDATE": "/Date(0)/",
        "STATUS":   "2",
        "NEGODATE": _fmt_sap_date(det.expiry_date if det else None),

        "VSART1": vsart_values[0], "VSART2": vsart_values[1],
        "VSART3": vsart_values[2], "VSART4": vsart_values[3],
        "FRTPYIND": _incoterm_freight(incoterm_str),

        "SHPPARTY1": ship_parties[0], "SHPPARTY2": ship_parties[1],
        "SHPPARTY3": ship_parties[2], "SHPPARTY4": ship_parties[3],

        "WERKS": werks,  "PAYMETH": "O",
        **{f"PURORDER{i+1}": purorders[i] for i in range(24)},

        "STOPIND": "X", "MATRIND": "X", "PDISIND": "X",
        "INTRIND": "X", "POIND":   "X", "PRICEIND": "X",

        "ADVBKC": "IN", "NEGBKC": "IN",
        "NEGBANK": (det.advising_bank if det else "") or "",

        "INTFREDY":  _fmt_int(lc_request.interest_free_credit_days),
        "INTRATE":   _fmt_decimal(lc_request.interest_charges),
        "USANCEPER": _fmt_int(lc_request.usance_period),
        "INSVALUE":  "1",

        "NOTE1":  note1_2[0],  "NOTE2":  note2_val,
        "NOTE3":  note3_5[0],  "NOTE4":  note3_5[1],  "NOTE5": note3_5[2],
        "NOTE6":  "",          "NOTE7":  "",           "NOTE8": "",
        "NOTE9":  note10_15[0], "NOTE10": note10_15[1], "NOTE11": note10_15[2],
        "NOTE12": note12_val,
        "NOTE13": note10_15[3], "NOTE14": note10_15[4], "NOTE15": note10_15[5],

        "to_items":   to_items,
        "to_results": {"Return": ""},
    }

    return payload

# ── Two-step SAP POST ─────────────────────────────────────────────────────────

def post_lc_to_sap(lc_request: LcRequest) -> dict:
    """
    Execute the two-step SAP OData create flow (CSRF-fetch then POST).

    On success, persists inward_no, lc_ref_no, and STATUS_SYNCED on the row.
    Returns {'success', 'status_code', 'sap_response', 'payload'}.
    """
    session = _make_session()
    payload = build_lc_payload(lc_request)

    # Step 1: fetch CSRF token
    try:
        csrf_resp = session.get(
            Constants.SAP_LC_URL,
            headers={"x-csrf-token": "Fetch"},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("SAP CSRF fetch failed: %s", exc)
        return {"success": False, "status_code": 503,
                "sap_response": "SAP unreachable during CSRF fetch: %s" % exc, "payload": payload}

    csrf_token = csrf_resp.headers.get("x-csrf-token") or csrf_resp.headers.get("X-CSRF-Token")
    if not csrf_token:
        logger.error(
            "SAP CSRF token missing in response. Status %s. Headers: %s",
            csrf_resp.status_code, dict(csrf_resp.headers),
        )
        return {"success": False, "status_code": csrf_resp.status_code,
                "sap_response": "No x-csrf-token returned by SAP", "payload": payload}

    logger.info("SAP CSRF token acquired (status %s)", csrf_resp.status_code)

    # Step 2: POST payload
    try:
        post_resp = session.post(
            Constants.SAP_LC_URL,
            json=payload,
            headers={"x-csrf-token": csrf_token},
            timeout=60,
        )
    except requests.RequestException as exc:
        logger.error("SAP POST failed: %s", exc)
        return {"success": False, "status_code": 503,
                "sap_response": "SAP unreachable during POST: %s" % exc, "payload": payload}

    try:
        sap_body = post_resp.json()
    except ValueError:
        sap_body = post_resp.text

    success = post_resp.status_code in (200, 201)

    if success:
        logger.info("SAP LC POST succeeded (status %s)", post_resp.status_code)
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
        logger.error("SAP LC POST failed (status %s): %s", post_resp.status_code, sap_body)

    return {
        "success": success, "status_code": post_resp.status_code,
        "sap_response": sap_body, "payload": payload,
    }