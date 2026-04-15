from django.urls import path
from .views import LCOCRView

urlpatterns = [
    path("ocr/", LCOCRView.as_view(), name="lc-ocr"),
]