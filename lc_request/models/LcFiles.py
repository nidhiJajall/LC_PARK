"""
LcFiles model — stores file attachments for LC Requests.

Files are uploaded to S3 when available, with a local filesystem fallback.
Both storage paths are logged so failures are always traceable.
"""
import logging
import os

from django.conf import settings
from django.db import models
from reversion import revisions as reversion

from api.models import BaseModel
from lc_request import Constants
from lc_request.functions import handle_file_upload_path

logger = logging.getLogger(__name__)


class LcFiles(BaseModel):
    """
    Represents a file attachment (PDF) associated with an LC Request.

    lc_details stores the primary key of the Y-flagged LcDetails entry
    (the OCR-extracted version) so the original document is always traceable.
    """

    file       = models.FileField(db_column='FILE', upload_to=handle_file_upload_path)
    category   = models.CharField(db_column='CATEGORY', max_length=20)
    status     = models.CharField(db_column='STATUS', max_length=50, default='active')
    password   = models.CharField(
        db_column='PASSWORD', max_length=128, blank=True, null=True,
    )
    lc_details = models.IntegerField(
        db_column='LC_DETAILS_ID', null=True, blank=True,
    )  # stores Y-entry pk

    def __str__(self):
        return '%s (%s)' % (self.category, self.file.name if self.file else 'no file')

    def save(self, *args, **kwargs):
        """
        Override save to upload the file to S3 before persisting the record.

        Falls back to local filesystem storage if S3 is unavailable.
        Both success and failure paths are logged with full context.
        """
        file_data = self.file

        # upload_to=handle_file_upload_path already runs when Django assigns the
        # FileField; calling it again here gives us the target path string for S3
        # without doubling the path on the FileField itself.
        if hasattr(file_data, 'name'):
            store_location = handle_file_upload_path(self, file_data.name)
        else:
            store_location = str(file_data)

        logger.info(
            'LcFiles.save: uploading file -- category: %s -- target: %s',
            self.category, store_location,
        )

        try:
            from s3_service.s3_service import S3Service
            s3_service = S3Service(
                settings.S3_BUCKET_NAME,
                os.path.join(settings.BASE_DIR, 'logs'),
            )
            s3_service.upload(file_data, store_location, 0, 0)
            self.file = store_location
            logger.info(
                'LcFiles.save: S3 upload success -- bucket: %s -- key: %s',
                settings.S3_BUCKET_NAME, store_location,
            )

        except Exception as exc:
            logger.warning(
                'LcFiles.save: S3 upload failed -- falling back to local storage'
                ' -- error: %s -- target: %s',
                exc, store_location,
            )
            logger.debug(
                'LcFiles.save: S3 upload traceback -- target: %s',
                store_location, exc_info=True,
            )
            try:
                from django.core.files.storage import FileSystemStorage
                file_location, file_name = store_location.rsplit('/', 1)
                local_dir = os.path.join(settings.MEDIA_ROOT, file_location)
                fs = FileSystemStorage(location=local_dir)
                fs.save(file_name, file_data)
                self.file = store_location
                logger.info(
                    'LcFiles.save: local storage success -- path: %s/%s',
                    local_dir, file_name,
                )
            except Exception as local_exc:
                logger.error(
                    'LcFiles.save: local storage also failed -- file will NOT be saved'
                    ' -- error: %s -- target: %s',
                    local_exc, store_location,
                )
                logger.debug(
                    'LcFiles.save: local storage traceback -- target: %s',
                    store_location, exc_info=True,
                )
                raise

        finally:
            super().save(*args, **kwargs)

    class Meta:
        db_table  = "TRANS_LC_FILES"
        app_label = Constants.APP_LABEL


reversion.register(LcFiles)
