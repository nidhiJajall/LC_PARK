from rest_framework.views import APIView
from rest_framework.response import Response

from .services import LCRequestService


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