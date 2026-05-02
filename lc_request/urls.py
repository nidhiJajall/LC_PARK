from django.urls import path
from .views import LCOCRView, LCRequestListCreateView, LCRequestDetailView, LCSAPPayloadPreviewView

urlpatterns = [
    path('ocr/', LCOCRView.as_view(), name='lc-ocr'),
    path('', LCRequestListCreateView.as_view(), name='lc-list-create'),
    path('<int:pk>/', LCRequestDetailView.as_view(), name='lc-detail'),
    path('<int:pk>/sync_to_sap/', LCSAPPayloadPreviewView.as_view(),name='lc-sap-payload-preview'),
]
