from django.contrib import admin
from .models import LcRequest, LcDetails, LcFiles

admin.site.register(LcRequest)
admin.site.register(LcDetails)
admin.site.register(LcFiles)