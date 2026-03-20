# lc_request/urls.py

from django.urls import path
from .views import LCRequestView, SOLookupView

urlpatterns = [
    # List + Create
    path("", LCRequestView.as_view(), name="lc-request-list-create"),
    path("so_lookup/", SOLookupView.as_view(),  name="lc-so-lookup"),
    path("<int:pk>/", LCRequestView.as_view(), name="lc-request-detail"),
]
