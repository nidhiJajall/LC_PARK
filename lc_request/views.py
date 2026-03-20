from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .services import LCRequestService


class LCRequestView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    service = LCRequestService()

    def get(self, request, pk=None):
        if pk:
            return self.service.get_lc_by_id(pk)
        return self.service.get_lc_list(request.query_params)

    def post(self, request):
        return self.service.create_lc_request(request.data)

    def patch(self, request, pk):
        return self.service.update_lc_request(pk, request.data)


class SOLookupView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    service = LCRequestService()

    def get(self, request):
        so_number = request.query_params.get("so_number")
        return self.service.get_so_details(request, so_number)  # ← pass request

