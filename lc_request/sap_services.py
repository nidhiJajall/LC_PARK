"""
SAP LC payload builder and two-step OData POST (CSRF-fetch → POST).

On success, extracts inward_no / lc_ref_no from the SAP return message
and persists them on the LcRequest row with status = STATUS_SYNCED.
Auth: HTTP Basic via SAP_USER / SAP_PASSWORD from Constants.

Logging convention:
  INFO  — CSRF acquired, POST dispatched, sync result
  WARNING — missing/unexpected SAP response fields
  ERROR — connection failures, non-2xx SAP responses, missing item data
  DEBUG — payload summary, SAP response body
"""
import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

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
    """
    Convert a Python date/str to SAP OData /Date(<ms>)/ format.

    Args:
        val: date, datetime, or date string (YYYY-MM-DD / DD.MM.YYYY / DD-MM-YYYY).

    Returns:
        SAP OData date string or '' for null/unparseable values.
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
            logger.debug('_fmt_sap_date: unrecognised date format %r — returning ""', val)
            return ""
    else:
        return ""
    return f"/Date({int(dt.timestamp() * 1000)})/"


def _incoterm_freight(incoterm: str) -> str:
    """
    Return 'PRE-PAID' for pre-paid incoterms, otherwise 'TO-PAY'.

    Args:
        incoterm: Incoterm string (e.g. 'CIF HAMBURG').

    Returns:
        'PRE-PAID' or 'TO-PAY'.
    """
    if not incoterm:
        return "TO-PAY"
    prepaid = {"CFR", "CIF", "CPT", "CIP", "DAP", "DAT", "DDP", "DPU"}
    code    = incoterm.strip().split()[0].upper()
    return "PRE-PAID" if code in prepaid else "TO-PAY"


def _split_text_to_notes(text: str, chunk_chars: int, num_chunks: int) -> list:
    """
    Split text into fixed-width chunks for SAP NOTE fields.

    Args:
        text: Source text to split.
        chunk_chars: Maximum characters per chunk.
        num_chunks: Number of chunks to return (unused slots are '').

    Returns:
        List of exactly num_chunks strings.
    """
    text = " ".join((text or "").replace("\n", " ").split())
    return [
        text[i * chunk_chars: (i + 1) * chunk_chars].strip()
        for i in range(num_chunks)
    ]


def _parse_tolerance(raw: str) -> tuple[str, str]:
    """
    Parse '10/10', '05/02', or '10' tolerance strings.

    Args:
        raw: Tolerance string from OCR or user input.

    Returns:
        Tuple of (qty_str, val_str) as plain integer strings.
    """
    if not raw:
        return "0", "0"
    raw = str(raw).strip()
    if "/" in raw:
        parts = raw.split("/", 1)
        try:
            return str(int(float(parts[0]))), str(int(float(parts[1])))
        except ValueError:
            logger.debug('_parse_tolerance: could not parse %r — returning "0","0"', raw)
            return "0", "0"
    try:
        v = str(int(float(raw)))
        return v, v
    except ValueError:
        logger.debug('_parse_tolerance: could not parse %r — returning "0","0"', raw)
        return "0", "0"


def _fmt_decimal(val, decimal_places: int = 2) -> str:
    """
    Format a numeric value as a fixed-decimal string.

    Args:
        val: Numeric value or None.
        decimal_places: Number of decimal places (default 2).

    Returns:
        Formatted string e.g. '1234.56', or '0.00' for None/empty.
    """
    if val is None or val == "":
        return f"0.{'0' * decimal_places}"
    try:
        return f"{Decimal(str(val)):.{decimal_places}f}"
    except (TypeError, ValueError, InvalidOperation):
        logger.debug('_fmt_decimal: could not format %r — returning zero', val)
        return f"0.{'0' * decimal_places}"


def _fmt_int(val) -> str:
    """
    Format an integer-like value as a plain string.

    Args:
        val: Numeric value or None.

    Returns:
        Integer string or '0' for None/empty.
    """
    if val is None or val == "":
        return "0"
    try:
        return str(int(val))
    except (TypeError, ValueError):
        logger.debug('_fmt_int: could not format %r — returning "0"', val)
        return "0"


def _parse_sap_return(sap_body: dict) -> tuple[str | None, str | None]:
    """
    Extract (inward_no, lc_ref_no) from the SAP response body.

    Expects sap_body['d']['to_results']['Return'] to contain the return message
    in the format: "Inward number <N> created successfully against LC number <N>".

    Args:
        sap_body: Parsed SAP JSON response dict.

    Returns:
        Tuple of (inward_no, lc_ref_no) or (None, None) if not found.
    """
    try:
        return_msg = sap_body["d"]["to_results"]["Return"]
    except (KeyError, TypeError):
        logger.warning(
            '_parse_sap_return: SAP response missing d.to_results.Return'
            ' — cannot extract reference numbers',
        )
        return None, None

    match = _SAP_RETURN_RE.search(str(return_msg))
    if not match:
        logger.warning(
            '_parse_sap_return: Return message did not match expected pattern'
            ' -- message: %r',
            str(return_msg)[:200],
        )
        return None, None

    inward_no = match.group(1).rstrip(".,;")
    lc_ref_no = match.group(2).rstrip(".,;")
    logger.debug(
        '_parse_sap_return: extracted inward_no=%s lc_ref_no=%s',
        inward_no, lc_ref_no,
    )
    return inward_no, lc_ref_no


# ── Payload builder ───────────────────────────────────────────────────────────

def build_lc_payload(lc_request: LcRequest) -> dict:
    """
    Build the complete SAP OData POST body for a single LcRequest.

    Data sources:
    - OCR extracted fields: lc_request.lc_details
    - User-entered fields: lc_request (interest, usance)
    - SO master data: lc_request.so_data (M2M)
    - Item data: Itemdata filtered by SO number

    Args:
        lc_request: LcRequest instance with lc_details and so_data prefetched.

    Returns:
        Plain dict ready for json.dumps / requests.post(json=...).

    Raises:
        ValueError: If any linked SO has no active Itemdata records.
    """
    det      = lc_request.lc_details
    so_list  = list(lc_request.so_data.all())
    first_so = so_list[0] if so_list else None

    logger.info(
        'build_lc_payload: building payload for LcRequest #%s'
        ' -- instrument: %s -- so_count: %d',
        lc_request.pk,
        det.instrument_number if det else '—',
        len(so_list),
    )

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

    cust_inv      = (det.cust_name_inv_print if det else "") or ""
    note1_2       = _split_text_to_notes(cust_inv, 35, 2)
    customer_name = (det.customer_name if det else "") or ""
    note2_val     = customer_name[:35] if customer_name else note1_2[1]

    adv_bank_addr = (det.advising_bank if det else "") or ""
    note3_5       = _split_text_to_notes(adv_bank_addr, 35, 3)
    add_cond      = (det.additional_condition_46a if det else "") or ""
    note10_15     = _split_text_to_notes(add_cond, 35, 6)
    clause78      = (det.clause_78 if det else "") or ""
    note12_val    = clause78[:35]

    to_items = []
    for so in so_list:
        items = Itemdata.objects.filter(
            so_number=so.so_number,
            status="Active",
        ).order_by("item_number")

        if not items.exists():
            logger.error(
                'build_lc_payload: no active Itemdata for SO %s'
                ' -- LcRequest #%s -- aborting payload build',
                so.so_number, lc_request.pk,
            )
            raise ValueError(
                "No active itemdata found for SO %s" % so.so_number
            )

        item_count = 0
        for row in items:
            to_items.append({
                "VBELN":     so.so_number,
                "POSNR":     str(row.item_number).zfill(6),
                "INSMATNO":  row.material_no,
                "MATLPRICE": _fmt_decimal(row.material_price),
                "INSQUAN":   _fmt_decimal(row.material_qty),
                "INSVAL":    "1",
                "INSQUANU":  row.unit,
            })
            item_count += 1

        logger.debug(
            'build_lc_payload: added %d item(s) for SO %s',
            item_count, so.so_number,
        )

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

        "NOTE1":  note1_2[0],   "NOTE2":  note2_val,
        "NOTE3":  note3_5[0],   "NOTE4":  note3_5[1],   "NOTE5":  note3_5[2],
        "NOTE6":  "",           "NOTE7":  "",            "NOTE8":  "",
        "NOTE9":  note10_15[0], "NOTE10": note10_15[1],  "NOTE11": note10_15[2],
        "NOTE12": note12_val,
        "NOTE13": note10_15[3], "NOTE14": note10_15[4],  "NOTE15": note10_15[5],

        "to_items":   to_items,
        "to_results": {"Return": ""},
    }

    logger.info(
        'build_lc_payload: payload built -- LcRequest #%s'
        ' -- item_count: %d -- so_count: %d',
        lc_request.pk, len(to_items), len(so_list),
    )
    return payload


# ── Two-step SAP POST ─────────────────────────────────────────────────────────

def post_lc_to_sap(lc_request: LcRequest) -> dict:
    """
    Execute the two-step SAP OData create flow (CSRF-fetch then POST).

    Step 1: GET with x-csrf-token: Fetch to obtain the CSRF token.
    Step 2: POST the payload with the acquired token.

    On success, persists inward_no, lc_ref_no, and STATUS_SYNCED on the row.

    Args:
        lc_request: LcRequest instance with lc_details and so_data prefetched.

    Returns:
        Dict with keys: success (bool), status_code (int),
        sap_response (dict|str), payload (dict).
    """
    logger.info(
        'post_lc_to_sap: starting SAP sync -- LcRequest #%s'
        ' -- instrument: %s',
        lc_request.pk,
        lc_request.lc_details.instrument_number
        if lc_request.lc_details else '—',
    )

    session = _make_session()
    payload = build_lc_payload(lc_request)

    # ── Step 1: fetch CSRF token ──────────────────────────────────────────────
    logger.debug(
        'post_lc_to_sap: fetching CSRF token -- url: %s', Constants.SAP_LC_URL,
    )
    try:
        csrf_resp = session.get(
            Constants.SAP_LC_URL,
            headers={"x-csrf-token": "Fetch"},
            timeout=30,
        )
    except requests.Timeout:
        logger.error(
            'post_lc_to_sap: CSRF fetch timed out -- LcRequest #%s', lc_request.pk,
        )
        return {
            "success": False, "status_code": 504,
            "sap_response": "SAP CSRF fetch timed out", "payload": payload,
        }
    except requests.RequestException as exc:
        logger.error(
            'post_lc_to_sap: CSRF fetch connection error -- LcRequest #%s -- %s',
            lc_request.pk, exc,
        )
        return {
            "success": False, "status_code": 503,
            "sap_response": "SAP unreachable during CSRF fetch: %s" % exc,
            "payload": payload,
        }

    csrf_token = (
        csrf_resp.headers.get("x-csrf-token")
        or csrf_resp.headers.get("X-CSRF-Token")
    )
    if not csrf_token:
        logger.error(
            'post_lc_to_sap: CSRF token missing in SAP response'
            ' -- LcRequest #%s -- http_status: %s',
            lc_request.pk, csrf_resp.status_code,
        )
        return {
            "success": False, "status_code": csrf_resp.status_code,
            "sap_response": "No x-csrf-token returned by SAP", "payload": payload,
        }

    logger.info(
        'post_lc_to_sap: CSRF token acquired -- LcRequest #%s'
        ' -- csrf_status: %s',
        lc_request.pk, csrf_resp.status_code,
    )

    # ── Step 2: POST payload ──────────────────────────────────────────────────
    logger.debug(
        'post_lc_to_sap: posting payload -- LcRequest #%s'
        ' -- item_count: %d',
        lc_request.pk, len(payload.get("to_items", [])),
    )
    try:
        post_resp = session.post(
            Constants.SAP_LC_URL,
            json=payload,
            headers={"x-csrf-token": csrf_token},
            timeout=60,
        )
    except requests.Timeout:
        logger.error(
            'post_lc_to_sap: POST timed out -- LcRequest #%s', lc_request.pk,
        )
        return {
            "success": False, "status_code": 504,
            "sap_response": "SAP POST timed out", "payload": payload,
        }
    except requests.RequestException as exc:
        logger.error(
            'post_lc_to_sap: POST connection error -- LcRequest #%s -- %s',
            lc_request.pk, exc,
        )
        return {
            "success": False, "status_code": 503,
            "sap_response": "SAP unreachable during POST: %s" % exc,
            "payload": payload,
        }

    try:
        sap_body = post_resp.json()
    except ValueError:
        sap_body = post_resp.text
        logger.warning(
            'post_lc_to_sap: SAP response is not JSON -- LcRequest #%s'
            ' -- body[:200]: %s',
            lc_request.pk, str(sap_body)[:200],
        )

    success = post_resp.status_code in (200, 201)

    if success:
        inward_no, lc_ref_no = _parse_sap_return(
            sap_body if isinstance(sap_body, dict) else {}
        )

        update_fields = ["request_status"]
        lc_request.request_status = Constants.STATUS_SYNCED

        if inward_no:
            lc_request.inward_no = inward_no
            update_fields.append("inward_no")
        if lc_ref_no:
            lc_request.lc_ref_no = lc_ref_no
            update_fields.append("lc_ref_no")

        lc_request.save(update_fields=update_fields)

        logger.info(
            'post_lc_to_sap: SAP sync success -- LcRequest #%s'
            ' -- sap_status: %s -- inward_no: %s -- lc_ref_no: %s',
            lc_request.pk, post_resp.status_code, inward_no, lc_ref_no,
        )
    else:
        logger.error(
            'post_lc_to_sap: SAP sync failed -- LcRequest #%s'
            ' -- sap_status: %s -- response: %s',
            lc_request.pk, post_resp.status_code,
            str(sap_body)[:500],
        )

    # ── Write SAP sync audit log ─────────────────────────────────────────────
    # Wrapped in try/except so a log failure NEVER affects the sync result.
    try:
        from lc_request.models.LcSapLog import LcSapLog
        LcSapLog.objects.create(
            lc_request_id=lc_request.pk,
            payload=payload,
            response=(
                sap_body
                if isinstance(sap_body, dict)
                else {"raw": str(sap_body)[:2000]}
            ),
            http_status=post_resp.status_code,
            success=success,
            synced_by=getattr(lc_request, "_synced_by", None),
        )
        logger.debug(
            "post_lc_to_sap: LcSapLog written -- LcRequest #%s", lc_request.pk,
        )
    except Exception as log_exc:
        logger.warning(
            "post_lc_to_sap: could not write LcSapLog -- LcRequest #%s -- %s",
            lc_request.pk, log_exc,
        )

    return {
        "success":      success,
        "status_code":  post_resp.status_code,
        "sap_response": sap_body,
        "payload":      payload,
    }