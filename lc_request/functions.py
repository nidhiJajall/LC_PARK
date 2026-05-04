"""Utility functions for the lc_request module."""
from datetime import datetime


def handle_file_upload_path(instance, filename: str) -> str:
    """
    Generate the upload path for an LC file.
    Format: LC/LC_FILES/<year>/<month>/<day>/<category>_<timestamp>.<ext>
    """
    parts    = filename.rsplit(".", 1)
    file_ext = parts[1] if len(parts) > 1 else None
    if file_ext is None:
        return filename

    now          = datetime.now()
    new_filename = "%s_%s.%s" % (instance.category, now.strftime("%d%m%y%H%M%S%f"), file_ext)
    today        = datetime.today()
    return "LC/LC_FILES/%d/%02d/%02d/%s" % (today.year, today.month, today.day, new_filename)