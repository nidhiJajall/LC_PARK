from django.db import models
from reversion import revisions as reversion
from api.models import BaseModel
from lc_request import Constants
from lc_request.functions import handle_file_upload_path


class LcFiles(BaseModel):
    file = models.FileField(db_column='FILE', upload_to=handle_file_upload_path)
    category = models.CharField(db_column='CATEGORY', max_length=20)
    status = models.CharField(db_column='STATUS', max_length=50, default='active')
    password = models.CharField(db_column='PASSWORD', max_length=128, blank=True, null=True)
    lc_details = models.IntegerField(db_column='LC_DETAILS_ID', null=True, blank=True)  # stores Y entry pk

    def __str__(self):
        return f"{self.category} ({self.file.name if self.file else 'no file'})"

    class Meta:
        db_table = 'TRANS_LC_FILES'
        app_label = Constants.APP_LABEL


reversion.register(LcFiles)