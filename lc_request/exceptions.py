"""
Custom exception classes for the lc_request module.

All exceptions inherit from a base LcRequestError and end with 'Error' suffix.
"""


class LcRequestError(Exception):
    """Base exception for all lc_request module errors."""
    pass


class LcRequestNotFoundError(LcRequestError):
    """Raised when an LC Request with the given ID does not exist."""
    pass


class LcDetailsNotFoundError(LcRequestError):
    """Raised when LC Details with the given ID or instrument number do not exist."""
    pass


class OcrServiceError(LcRequestError):
    """Raised when the OCR service is unavailable or returns an error."""
    pass


class OcrExtractionError(LcRequestError):
    """Raised when OCR extraction fails or returns invalid data."""
    pass


class SapSyncError(LcRequestError):
    """Raised when SAP synchronization fails."""
    pass


class SapConnectionError(SapSyncError):
    """Raised when unable to connect to SAP OData service."""
    pass


class SapCsrfTokenError(SapSyncError):
    """Raised when SAP CSRF token fetch fails."""
    pass


class SapPayloadError(SapSyncError):
    """Raised when SAP payload construction fails."""
    pass


class InvalidLcStatusError(LcRequestError):
    """Raised when attempting an operation on an LC Request with invalid status."""
    pass


class FileUploadError(LcRequestError):
    """Raised when file upload to S3 or local storage fails."""
    pass


class InvalidFileTypeError(LcRequestError):
    """Raised when uploaded file type is not allowed."""
    pass


class SoDataNotFoundError(LcRequestError):
    """Raised when SO (Sales Order) data lookup fails."""
    pass


class InvalidSoDataError(LcRequestError):
    """Raised when SO data validation fails (payment term, customer code mismatch, etc.)."""
    pass
