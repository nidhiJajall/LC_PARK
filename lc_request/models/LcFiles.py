import os
from django.db import models
from django.conf import settings
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

    def save(self, *args, **kwargs):
        file_data = self.file
        store_location = handle_file_upload_path(self, self.file.name)

        try:
            from s3_service.s3_service import S3Service
            s3_service = S3Service(settings.S3_BUCKET_NAME, os.path.join(settings.BASE_DIR, 'logs'))
            s3_service.upload(file_data, store_location, 0, 0)
            self.file = store_location
        except Exception as e:
            from django.core.files.storage import FileSystemStorage
            [file_location, file_name] = store_location.rsplit('/', 1)
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, file_location))
            fs.save(file_name, file_data)
            self.file = store_location
        finally:
            super().save(*args, **kwargs)

    class Meta:
        db_table = "TRANS_LC_FILES"
        app_label = Constants.APP_LABEL


reversion.register(LcFiles)