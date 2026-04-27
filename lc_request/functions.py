from datetime import datetime


def handle_file_upload_path(instance, filename):
    """
    To generate file upload path for LC app.
    """
    file_split = filename.rsplit(".", 1)
    file_type = file_split[1] if len(file_split) > 1 else None
    if file_type is None:
        return filename
    new_filename = instance.category + "_" + datetime.now().strftime(
        "%d%m%y%H%M%S%f") + "." + file_type
    today = datetime.today()
    return f"LC/LC_FILES/{today.year}/{today.month:02d}/{today.day:02d}/{new_filename}"