# lc_request/views.py
# ─────────────────────────────────────────────────────────────────────────────
# Views are intentionally thin: they only handle the HTTP layer (routing,
# basic request inspection) and delegate ALL business / DB / external-API
# logic to ``LCRequestService`` in services.py.
#
# WHY no DB calls or requests.post() here?
#   Keeping views.py free of business logic means the service methods can be
#   unit-tested directly without an HTTP request/response cycle.
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework.request  import Request
from rest_framework.response import Response
from rest_framework.views    import APIView

from .services import LCRequestService


class LCOCRView(APIView):
    """
    POST /lc_request/ocr/

    Accepts a multipart POST containing the LC document under the key
    ``file``.  Delegates to ``LCRequestService.extract_and_save()``, which:

    1. Proxies the PDF to the external OCR engine.
    2. Creates a draft ``LCRequest`` from the extracted fields and records
       Version 1 in django-reversion.
    3. Returns the OCR prediction together with the new ``lc_id``.

    The frontend stores ``lc_id`` and switches subsequent save calls from
    POST (create) → PATCH (update), so the same draft is updated rather than
    a new record being created on every save.

    WHY no authentication / permission classes?
      This endpoint is reached from the same internal network; authentication
      is enforced at the reverse-proxy / WAF layer before the request
      arrives.  Add ``IsAuthenticated`` here if that policy changes.
    """

    authentication_classes = []
    permission_classes     = []

    def post(self, request: Request) -> Response:
        service = LCRequestService()
        return service.extract_and_save(request)