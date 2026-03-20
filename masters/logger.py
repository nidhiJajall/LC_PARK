import os

from django.conf import settings
from logging_essar import init_logging

lcparkLogs = init_logging(log_name='lcparkLogs', log_level="DEBUG", rotation_criteria='time',
                        rotate_interval=1, rotate_when='d', backup_count=30,
                        log_directory=os.path.join(settings.BASE_DIR, 'logs'),enable_mailing = False)