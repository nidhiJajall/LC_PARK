"""
URL configuration for lcpark project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin sits under the same prefix as the rest of the project
    path('lcpark/admin/', admin.site.urls),
    path('lcpark/', include('api.urls')),
    path('lcpark/lc_request/', include('lc_request.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )