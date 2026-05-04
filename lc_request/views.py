"""
API views for the lc_request module.

All business logic is delegated to LCRequestService; views handle only
request routing, authentication, and response dispatch.
"""
import logging
import os
import traceback

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LcFiles, LcRequest
from .sap_services import build_lc_payload, post_lc_to_sap
from .services import LCRequestService

logger = logging.getLogger(__name__)


class LCOCRView(APIView):
    """POST: Forward an uploaded PDF to the OCR service and return extracted fields."""

    authentication_classes = []
    permission_classes     = []

    def post(self, request):
        return LCRequestService().extract_ocr_data(request)


class LCRequestListCreateView(APIView):
    """GET: paginated list of LC Requests. POST: create a new LC Request."""

    authentication_classes = []
    permission_classes     = []

    def get(self, request):
        return LCRequestService().get_lc_list(request.query_params)

    def post(self, request):
        return LCRequestService().create_lc_request(request)


class LCRequestDetailView(APIView):
    """GET: retrieve a single LC Request. PATCH: update it."""

    authentication_classes = []
    permission_classes     = []

    def get(self, request, pk):
        return LCRequestService().get_lc_by_id(pk)

    def patch(self, request, pk):
        return LCRequestService().update_lc_request(request, pk)


class LCFilesView(APIView):
    """GET: download a file by its LcFiles primary key (S3 with local fallback)."""

    authentication_classes = []
    permission_classes     = []

    def get(self, request, **kwargs):
        file_pk = kwargs.get('id')
        logger.info('File download requested by user %s for LcFiles #%s', request.user, file_pk)

        try:
            file_obj  = LcFiles.objects.get(pk=file_pk)
            file_name = os.path.basename(file_obj.file.name)
            file_path = file_obj.file.name

            try:
                from s3_service.s3_service import S3Service
                s3_service = S3Service(settings.S3_BUCKET_NAME, os.path.join(settings.BASE_DIR, 'logs'))
                file_key   = file_path.replace(settings.MEDIA_ROOT, "").replace("\\", "/").lstrip("/")
                logger.info('Downloading file from S3 key %s (LcFiles #%s)', file_key, file_pk)
                file_data  = s3_service.download(file_key)
            except Exception:
                logger.warning('S3 download failed for LcFiles #%s — falling back to local storage', file_pk)
                logger.debug(traceback.format_exc())
                file_data = open(os.path.join(settings.MEDIA_ROOT, file_path), 'rb')

            response = HttpResponse(file_data, content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename={file_name}'
            logger.info('File download response sent for LcFiles #%s', file_pk)
            return response

        except Exception as exc:
            logger.error('File download failed for LcFiles #%s: %s', file_pk, exc)
            logger.debug(traceback.format_exc())
            return Response({"error": "Unable to download file"}, status=status.HTTP_400_BAD_REQUEST)


class LCSAPPayloadPreviewView(APIView):
    """
    GET  /<pk>/sync_to_sap/ — preview the SAP payload without posting (dry-run).
    POST /<pk>/sync_to_sap/ — execute the CSRF-fetch + POST flow to SAP.
    """

    authentication_classes = []
    permission_classes     = []

    def _get_lc(self, pk) -> LcRequest:
        return (
            LcRequest.objects
            .select_related("lc_details")
            .prefetch_related("so_data")
            .get(pk=pk)
        )

    def get(self, request, pk):
        """Return a preview of the SAP payload without actually sending it."""
        try:
            lc_request = self._get_lc(pk)
            payload    = build_lc_payload(lc_request)
            logger.info('SAP payload preview generated for LcRequest #%s', pk)
            return Response({"validated": True, "payload": payload})
        except LcRequest.DoesNotExist:
            return Response({"error": "LC Request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.error('SAP payload build error for LcRequest #%s: %s', pk, exc)
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk):
        """Sync the LC Request to SAP; persist inward_no / lc_ref_no on success."""
        try:
            lc_request = self._get_lc(pk)
        except LcRequest.DoesNotExist:
            return Response({"error": "LC Request not found"}, status=status.HTTP_404_NOT_FOUND)

        logger.info('SAP sync initiated for LcRequest #%s', pk)
        result = post_lc_to_sap(lc_request)

        if result["success"]:
            logger.info('SAP sync succeeded for LcRequest #%s', pk)
            return Response(
                {
                    "message":      "LC Request synced to SAP successfully.",
                    "sap_response": result["sap_response"],
                    "payload":      result["payload"],
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "error":        "SAP sync failed.",
                    "sap_response": result["sap_response"],
                    "status_code":  result["status_code"],
                    "payload":      result["payload"],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )