"""
API views for the lc_request module.

All business logic is delegated to LCRequestService; views handle only
request routing, authentication, and response dispatch.

Logging convention (matches framework format):
  INFO  — every inbound request and successful response
  WARNING — recoverable issues (not found, bad input)
  ERROR — unexpected failures with full context
  DEBUG — detailed diagnostic data (tracebacks, payloads)
"""
import logging
import os
import traceback

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LcFiles, LcRequest
from .sap_services import build_lc_payload, post_lc_to_sap
from .services import LCRequestService

logger = logging.getLogger(__name__)


def _get_client_ip(request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For from proxies."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


class LCOCRView(APIView):
    """POST: Forward an uploaded PDF to the OCR service and return extracted fields."""

    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        """
        Args:
            request: DRF request with FILES['file'] containing the PDF.

        Returns:
            Response: OCR extraction result or error detail.
        """
        user = request.user
        ip   = _get_client_ip(request)
        file_name = request.FILES.get('file', {}).name if request.FILES.get('file') else 'no file'
        logger.info(
            'OCR request -- user: %s -- ip: %s -- file: %s',
            user, ip, file_name,
        )
        response = LCRequestService().extract_ocr_data(request)
        logger.info(
            'OCR response -- user: %s -- ip: %s -- status: %s',
            user, ip, response.status_code,
        )
        return response


class LCRequestListCreateView(APIView):
    """GET: paginated list of LC Requests. POST: create a new LC Request."""

    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        """
        Args:
            request: DRF request with optional query params: page, pageSize, search, filter.

        Returns:
            Response: Paginated list with total count and results.
        """
        user = request.user
        ip   = _get_client_ip(request)
        logger.info(
            'LC list request -- user: %s -- ip: %s -- params: %s',
            user, ip, dict(request.query_params),
        )
        response = LCRequestService().get_lc_list(request.query_params)
        logger.info(
            'LC list response -- user: %s -- ip: %s -- status: %s',
            user, ip, response.status_code,
        )
        return response

    def post(self, request):
        """
        Args:
            request: DRF request with LC fields and optional file in FILES.

        Returns:
            Response: Created LcRequest detail or validation error.
        """
        user = request.user
        ip   = _get_client_ip(request)
        logger.info(
            'LC create request -- user: %s -- ip: %s -- status_field: %s',
            user, ip, request.data.get('status', 'draft'),
        )
        response = LCRequestService().create_lc_request(request)
        logger.info(
            'LC create response -- user: %s -- ip: %s -- http_status: %s',
            user, ip, response.status_code,
        )
        return response


class LCRequestDetailView(APIView):
    """GET: retrieve a single LC Request. PATCH: update it."""

    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        """
        Args:
            request: DRF request.
            pk: Primary key of the LcRequest to retrieve.

        Returns:
            Response: Full LcRequest detail or 404.
        """
        user = request.user
        ip   = _get_client_ip(request)
        logger.info(
            'LC detail request -- user: %s -- ip: %s -- pk: %s',
            user, ip, pk,
        )
        response = LCRequestService().get_lc_by_id(pk)
        logger.info(
            'LC detail response -- user: %s -- ip: %s -- pk: %s -- status: %s',
            user, ip, pk, response.status_code,
        )
        return response

    def patch(self, request, pk):
        """
        Args:
            request: DRF request with fields to update.
            pk: Primary key of the LcRequest to update.

        Returns:
            Response: Updated LcRequest detail or error.
        """
        user = request.user
        ip   = _get_client_ip(request)
        logger.info(
            'LC update request -- user: %s -- ip: %s -- pk: %s -- status_field: %s',
            user, ip, pk, request.data.get('status', 'unchanged'),
        )
        response = LCRequestService().update_lc_request(request, pk)
        logger.info(
            'LC update response -- user: %s -- ip: %s -- pk: %s -- http_status: %s',
            user, ip, pk, response.status_code,
        )
        return response


class LCFilesView(APIView):
    """GET: download a file by its LcFiles primary key (S3 with local fallback)."""

    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, **kwargs):
        """
        Args:
            request: DRF request.
            id (kwarg): Primary key of the LcFiles record to download.

        Returns:
            HttpResponse: File attachment or error response.
        """
        file_pk = kwargs.get('id')
        user    = request.user
        ip      = _get_client_ip(request)

        logger.info(
            'File download request -- user: %s -- ip: %s -- file_pk: %s',
            user, ip, file_pk,
        )

        try:
            file_obj  = LcFiles.objects.get(pk=file_pk)
            file_name = os.path.basename(file_obj.file.name)
            file_path = file_obj.file.name

            try:
                from s3_service.s3_service import S3Service
                s3_service = S3Service(
                    settings.S3_BUCKET_NAME,
                    os.path.join(settings.BASE_DIR, 'logs'),
                )
                file_key  = (
                    file_path
                    .replace(settings.MEDIA_ROOT, "")
                    .replace("\\", "/")
                    .lstrip("/")
                )
                logger.debug(
                    'S3 download attempt -- user: %s -- file_pk: %s -- key: %s',
                    user, file_pk, file_key,
                )
                file_data = s3_service.download(file_key)
                logger.info(
                    'S3 download success -- user: %s -- file_pk: %s -- key: %s',
                    user, file_pk, file_key,
                )

            except Exception:
                logger.warning(
                    'S3 download failed -- user: %s -- file_pk: %s -- falling back to local',
                    user, file_pk,
                )
                logger.debug(
                    'S3 download traceback -- file_pk: %s\n%s',
                    file_pk, traceback.format_exc(),
                )
                local_path = os.path.join(settings.MEDIA_ROOT, file_path)
                file_data  = open(local_path, 'rb')  # noqa: WPS515
                logger.info(
                    'Local file opened -- user: %s -- file_pk: %s -- path: %s',
                    user, file_pk, local_path,
                )

            response = HttpResponse(file_data, content_type='application/force-download')
            response['Content-Disposition'] = f'attachment; filename={file_name}'
            logger.info(
                'File download sent -- user: %s -- ip: %s -- file_pk: %s -- name: %s',
                user, ip, file_pk, file_name,
            )
            return response

        except LcFiles.DoesNotExist:
            logger.warning(
                'File not found -- user: %s -- ip: %s -- file_pk: %s',
                user, ip, file_pk,
            )
            return Response(
                {"error": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.error(
                'File download error -- user: %s -- ip: %s -- file_pk: %s -- error: %s',
                user, ip, file_pk, exc,
            )
            logger.debug(
                'File download traceback -- file_pk: %s\n%s',
                file_pk, traceback.format_exc(),
            )
            return Response(
                {"error": "Unable to download file"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LCSAPPayloadPreviewView(APIView):
    """
    GET  /<pk>/sync_to_sap/ — preview the SAP payload without posting (dry-run).
    POST /<pk>/sync_to_sap/ — execute the CSRF-fetch + POST flow to SAP.
    """

    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def _get_lc(self, pk) -> LcRequest:
        """
        Fetch LcRequest with related data for SAP operations.

        Args:
            pk: Primary key of the LcRequest.

        Returns:
            LcRequest: Instance with lc_details and so_data prefetched.

        Raises:
            LcRequest.DoesNotExist: If no record matches pk.
        """
        return (
            LcRequest.objects
            .select_related("lc_details")
            .prefetch_related("so_data")
            .get(pk=pk)
        )

    def get(self, request, pk):
        """
        Return a preview of the SAP payload without actually sending it.

        Args:
            request: DRF request.
            pk: Primary key of the LcRequest.

        Returns:
            Response: Validated payload dict or error.
        """
        user = request.user
        ip   = _get_client_ip(request)
        logger.info(
            'SAP payload preview request -- user: %s -- ip: %s -- pk: %s',
            user, ip, pk,
        )
        try:
            lc_request = self._get_lc(pk)
            payload    = build_lc_payload(lc_request)
            logger.info(
                'SAP payload preview success -- user: %s -- pk: %s -- so_count: %s',
                user, pk, lc_request.so_data.count(),
            )
            return Response({"validated": True, "payload": payload})

        except LcRequest.DoesNotExist:
            logger.warning(
                'SAP preview -- LC not found -- user: %s -- ip: %s -- pk: %s',
                user, ip, pk,
            )
            return Response(
                {"error": "LC Request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.error(
                'SAP payload build error -- user: %s -- ip: %s -- pk: %s -- error: %s',
                user, ip, pk, exc,
            )
            logger.debug(
                'SAP payload build traceback -- pk: %s\n%s',
                pk, traceback.format_exc(),
            )
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk):
        """
        Sync the LC Request to SAP; persist inward_no / lc_ref_no on success.

        Args:
            request: DRF request.
            pk: Primary key of the LcRequest to sync.

        Returns:
            Response: SAP sync result with inward_no / lc_ref_no or error.
        """
        user = request.user
        ip   = _get_client_ip(request)
        logger.info(
            'SAP sync request -- user: %s -- ip: %s -- pk: %s',
            user, ip, pk,
        )

        try:
            lc_request = self._get_lc(pk)
        except LcRequest.DoesNotExist:
            logger.warning(
                'SAP sync -- LC not found -- user: %s -- ip: %s -- pk: %s',
                user, ip, pk,
            )
            return Response(
                {"error": "LC Request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        lc_request._synced_by = str(request.user)
        result = post_lc_to_sap(lc_request)

        if result["success"]:
            logger.info(
                'SAP sync success -- user: %s -- ip: %s -- pk: %s'
                ' -- inward_no: %s -- lc_ref_no: %s',
                user, ip, pk,
                lc_request.inward_no, lc_request.lc_ref_no,
            )
            return Response(
                {
                    "message":      "LC Request synced to SAP successfully.",
                    "sap_response": result["sap_response"],
                    "payload":      result["payload"],
                },
                status=status.HTTP_200_OK,
            )

        logger.error(
            'SAP sync failed -- user: %s -- ip: %s -- pk: %s -- sap_status: %s',
            user, ip, pk, result["status_code"],
        )
        return Response(
            {
                "error":        "SAP sync failed.",
                "sap_response": result["sap_response"],
                "status_code":  result["status_code"],
                "payload":      result["payload"],
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )


class LcSapLogListView(APIView):
    """GET /<pk>/sap_logs/ — return all SAP sync log entries for an LC Request."""

    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        ip   = _get_client_ip(request)
        logger.info('SAP log list -- user: %s -- ip: %s -- pk: %s', user, ip, pk)

        if not LcRequest.objects.filter(pk=pk).exists():
            return Response({"error": "LC Request not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            from lc_request.models.LcSapLog import LcSapLog
        except ImportError:
            logger.error('LcSapLogListView: LcSapLog not found — run migrations')
            return Response({"results": []})

        from rest_framework import serializers as drf_serializers

        class _LogSerializer(drf_serializers.Serializer):
            id            = drf_serializers.IntegerField()
            lc_request_id = drf_serializers.IntegerField()
            payload       = drf_serializers.JSONField()
            response      = drf_serializers.JSONField()
            http_status   = drf_serializers.IntegerField()
            success       = drf_serializers.BooleanField()
            synced_by     = drf_serializers.CharField(allow_null=True)
            created_date  = drf_serializers.DateTimeField()

        logs = LcSapLog.objects.filter(lc_request_id=pk).order_by("-created_date")
        return Response({"results": _LogSerializer(logs, many=True).data})