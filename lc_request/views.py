import os

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

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

    def get(self, request, uid):
        try:
            if not uid:
                return Response({"error": "File ID is missing"}, status=status.HTTP_400_BAD_REQUEST)

            lc_file = LcFiles.objects.filter(pk=uid, is_active=True, is_deleted=False).first()
            if not lc_file:
                return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

            from django.conf import settings
            s3_key = str(lc_file.file).lstrip("/").replace("\\", "/")
            file_bytes = None

            try:
                from s3_service.s3_service import S3Service
                s3_service = S3Service(settings.S3_BUCKET_NAME, os.path.join(settings.BASE_DIR, 'logs'))
                file_bytes = s3_service.download(s3_key)
            except Exception:
                file_bytes = open(os.path.join(settings.MEDIA_ROOT, s3_key), "rb")

            response = HttpResponse(file_bytes, content_type='application/force-download')
            response['Content-Disposition'] = 'attachment; filename=download.pdf'
            return response

        except FileNotFoundError:
            return Response({"error": "Could not find file"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Could not download file"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
