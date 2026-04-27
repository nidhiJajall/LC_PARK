"""
Utility functions for the LC app.

File upload path mirrors fi_vendor/functions.py.  Django's DEFAULT_FILE_STORAGE
(configured to S3Boto3Storage in settings) handles actual S3 upload transparently —
only the storage path string is defined here.
"""
from datetime import datetime


def handle_file_upload_path(instance, filename: str) -> str:
    """
    Generate S3-compatible storage path for LC file attachments.

    Path pattern:
        LC/<lc_request_id>/<category>/<category>_<timestamp>.<ext>

    Example:
        LC/42/LC_DOCUMENT/LC_DOCUMENT_230425143022123456.pdf

    Args:
        instance: ``LCFiles`` model instance (lc_request_id and category must exist).
        filename: Original filename from the upload.

    Returns:
        Storage path string consumed by Django's file storage backend.
    """
    file_parts  = filename.rsplit(".", 1)
    extension   = file_parts[1] if len(file_parts) > 1 else "bin"
    category    = getattr(instance, "category", "MISC")
    timestamp   = datetime.now().strftime("%d%m%y%H%M%S%f")
    new_filename = f"{category}_{timestamp}.{extension}"

    lc_request_id = getattr(instance, "lc_request_id", "unknown")
    return f"LC/{lc_request_id}/{category}/{new_filename}"


def reduce_filename(file_data: dict) -> dict:
    """
    Truncate filenames that exceed 100 characters to avoid DB column overflow.
    Mirrors ``reduceFileName`` in fi_vendor/helper_functions.py.

    Args:
        file_data: Dict with a ``file`` key pointing to an in-memory uploaded file.

    Returns:
        The same dict with the filename truncated if necessary.
    """
    uploaded_file       = file_data["file"]
    complete_name       = uploaded_file.name
    name_part, _, ext   = complete_name.rpartition(".")

    if len(complete_name) > 100:
        name_part            = complete_name[:95]
        uploaded_file.name   = f"{name_part}.{ext}"
        file_data["file"]    = uploaded_file

    return file_data
