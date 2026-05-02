import os

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from logs import lcparkLogs as logs
from .sap_services import build_lc_payload, post_lc_to_sap
import traceback
from .models import LcRequest

from .services import LCRequestService
from .models import LcFiles


class LCOCRView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        service = LCRequestService()
        return service.extract_ocr_data(request)


class LCRequestListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        service = LCRequestService()
        return service.get_lc_list(request.query_params)

    def post(self, request):
        service = LCRequestService()
        return service.create_lc_request(request)


class LCRequestDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk):
        service = LCRequestService()
        return service.get_lc_by_id(pk)

    def patch(self, request, pk):
        service = LCRequestService()
        return service.update_lc_request(request, pk)


class LCFilesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, **kwargs):
        try:
            logs.info("REQUESTED TO DOWNLOAD FILE BY [%s]", request.user.username)

            file_obj = LcFiles.objects.get(pk=kwargs.get('id'))
            file_name = os.path.basename(file_obj.file.name)
            file_path = file_obj.file.name

            try:
                from s3_service.s3_service import S3Service
                s3_service = S3Service(settings.S3_BUCKET_NAME, os.path.join(settings.BASE_DIR, 'logs'))
                file_key = file_path.replace(settings.MEDIA_ROOT, "").replace("\\", "/").lstrip("/")
                logs.Info("DOWNLOADING FILE FROM S3 BUCKET [%s] FOR PK [%s]", file_key, kwargs.get('id'))
                file_data = s3_service.download(file_key)
            except Exception:
                logs.Error("S3 DOWNLOAD FAILED, FALLING BACK TO LOCAL STORAGE")
                logs.Error(traceback.format_exc())
                file_data = open(os.path.join(settings.MEDIA_ROOT, file_path), 'rb')

            response = HttpResponse(file_data, content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename={file_name}'
            logs.Info("DOWNLOAD RESPONSE SENT FOR PK [%s]", kwargs.get('id'))
            return response
        except Exception as exc:
            logs.Error("EXCEPTION OCCURRED WHILE FILE DOWNLOAD FOR USER [%s]", request.user.username)
            logs.Error(exc)
            logs.Error(traceback.format_exc())
            return Response({"error": "Unable to download file"}, status=status.HTTP_400_BAD_REQUEST)


class LCSAPPayloadPreviewView(APIView):
    """
    GET  /<pk>/sync_to_sap/  →  preview the SAP payload without posting
    POST /<pk>/sync_to_sap/  →  execute the two-step CSRF + POST to SAP
    """
    authentication_classes = []
    permission_classes = []

    def _get_lc(self, pk):
        return (
            LcRequest.objects
            .select_related("lc_details")
            .prefetch_related("so_data")
            .get(pk=pk)
        )

    # ── Preview (dry-run) ──────────────────────────────────────────────────────
    def get(self, request, pk):
        try:
            lc_request = self._get_lc(pk)
            payload = build_lc_payload(lc_request)
            return Response({"validated": True, "payload": payload})

        except LcRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ── Actual sync to SAP ─────────────────────────────────────────────────────
    def post(self, request, pk):
        try:
            lc_request = self._get_lc(pk)
        except LcRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = post_lc_to_sap(lc_request)

        if result["success"]:
            return Response(
                {
                    "message": "LC Request synced to SAP successfully.",
                    "sap_response": result["sap_response"],
                    "payload": result["payload"],
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "error": "SAP sync failed.",
                    "sap_response": result["sap_response"],
                    "status_code": result["status_code"],
                    "payload": result["payload"],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )