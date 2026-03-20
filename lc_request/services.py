
# lc_request/services.py
# ─────────────────────────────────────────────────────────────────────────────
# All business logic lives here — views.py never touches the DB directly.
# Mirrors their TaskService pattern exactly.
# ─────────────────────────────────────────────────────────────────────────────
import json
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.paginator import Paginator
from rest_framework.response import Response
from rest_framework import status

from .models import LCRequest, LCSODetail
from .serializers import LCRequestSerializer, LCRequestWriteSerializer


class LCRequestService:
    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPER — parse so_details JSON string and save child rows
    # Called internally by create and update methods
    # ─────────────────────────────────────────────────────────────────────────
    def _save_so_details(self, lc_instance, so_details_raw):
        if not so_details_raw:
            return
        try:
            so_list = json.loads(so_details_raw)
        except (json.JSONDecodeError, TypeError):
            return
        # Delete old rows, re-create fresh from submitted data
        LCSODetail.objects.filter(lc_request=lc_instance).delete()
        rows = [
            LCSODetail(
                lc_request=lc_instance,
                so_number=row.get("so_number", ""),
                interest_free_credit_days=row.get("interest_free_credit_days"),
                interest_charges=row.get("interest_charges"),
                usance_period=row.get("usance_period"),
            )
            for row in so_list
        ]
        LCSODetail.objects.bulk_create(rows)

    # ─────────────────────────────────────────────────────────────────────────
    # GET LIST — paginated, with optional search and filter
    # ─────────────────────────────────────────────────────────────────────────
    def get_lc_list(self, query_params):
        queryset = LCRequest.objects.all()
        # Search across customer_code, company_code, status (AND semantics)
        search = query_params.get("search", None)
        if search:
            queryset = (
                queryset.filter(customer_code__icontains=search)
                .filter(company_code__icontains=search)
                .filter(status__icontains=search)
            )
        # Filter by status when ?filter=1 is passed
        if query_params.get("filter"):
            filter_status = query_params.get("status")
            if filter_status:
                queryset = queryset.filter(status=filter_status)
        # Paginate
        page_size = int(query_params.get("pageSize", 20))
        page_no = int(query_params.get("page", 1))
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_no)
        serializer = LCRequestSerializer(page_obj.object_list, many=True)
        return Response({
            "total": paginator.count,
            "results": serializer.data,
        })

    # ─────────────────────────────────────────────────────────────────────────
    # GET SINGLE
    # ─────────────────────────────────────────────────────────────────────────
    def get_lc_by_id(self, pk):
        try:
            instance = LCRequest.objects.get(pk=pk)
            return Response(LCRequestSerializer(instance).data)
        except LCRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────
    def create_lc_request(self, data):
        serializer = LCRequestWriteSerializer(data=data)
        if serializer.is_valid():
            lc_instance = serializer.save()
            self._save_so_details(lc_instance, data.get("so_details"))
            return Response(
                LCRequestSerializer(lc_instance).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE (PATCH)
    # ─────────────────────────────────────────────────────────────────────────
    def update_lc_request(self, pk, data):
        try:
            instance = LCRequest.objects.get(pk=pk)
            serializer = LCRequestWriteSerializer(instance, data=data, partial=True)
            if serializer.is_valid():
                lc_instance = serializer.save()
                if data.get("so_details"):
                    self._save_so_details(lc_instance, data.get("so_details"))
                return Response(LCRequestSerializer(lc_instance).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LCRequest.DoesNotExist:
            return Response(
                {"error": "LC Request not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # SO LOOKUP — proxy to Masters API (SWFramework)
    # ─────────────────────────────────────────────────────────────────────────
    def get_so_details(self, request, so_number):
        if not so_number:
            return Response(
                {"error": "so_number is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build Masters endpoint from settings (with safe defaults for dev)
        prefix = getattr(settings, "PROJECT_API_PREFIX", "testproject")
        master_route = getattr(settings, "MASTERS_ROUTE", "master")
        app_model = getattr(settings, "MASTERS_SODATA_APP_MODEL", "Master.Sodata")

        base = f"{request.scheme}://{request.get_host()}"
        qs = urlencode({
            "page": 1,
            "pageSize": 20,
            "so_number": so_number,
            "filter": 1,
        })
        url = f"{base}/{prefix}/{master_route}/{app_model}/list?{qs}"

        # Forward Authorization + typical SWF headers
        headers = {
            "Authorization": request.META.get("HTTP_AUTHORIZATION", ""),
            "Accept": "application/json",
            "source": "workflow",
            "req": "list",
        }

        try:
            r = requests.get(url, headers=headers, timeout=15)
            data = r.json()
            return Response(data, status=r.status_code)
        except Exception as ex:
            return Response(
                {"error": f"Upstream error: {ex}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
