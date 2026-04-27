from django.urls import path
from .views import LCOCRView, LCRequestListCreateView, LCRequestDetailView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('ocr/', LCOCRView.as_view(), name='lc-ocr'),
    path('', LCRequestListCreateView.as_view(), name='lc-list-create'),
    path('<int:pk>/', LCRequestDetailView.as_view(), name='lc-detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)