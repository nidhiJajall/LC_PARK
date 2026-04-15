from django.contrib import admin
from .models import LCRequest, LCSODetail, SODetail

admin.site.register(LCRequest)
admin.site.register(LCSODetail)
admin.site.register(SODetail)