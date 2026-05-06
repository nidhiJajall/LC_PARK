"""
Proxy models with business logic for the lc_request module.

Entities contain pure, atomic, single-responsibility methods that operate
only on instance variables and arguments — no infrastructure calls.
"""
from decimal import Decimal
from datetime import datetime

from .models import LcRequest, LcDetails, LcFiles
from .manager import LCFileManager


class LcRequestProxy(LcRequest):
    """
    Proxy model for LcRequest with business logic.
    
    Represents an LC (Letter of Credit) request with associated details,
    SO data, and lifecycle status transitions.
    """
    
    objects = None  # Will be set to custom manager when created
    
    class Meta:
        proxy = True
    
    def is_draft(self) -> bool:
        """Return True if this LC Request is in draft status."""
        from lc_request import Constants
        return self.request_status == Constants.STATUS_DRAFT
    
    def is_submitted(self) -> bool:
        """Return True if this LC Request has been submitted."""
        from lc_request import Constants
        return self.request_status == Constants.STATUS_SUBMITTED
    
    def is_synced(self) -> bool:
        """Return True if this LC Request has been synced to SAP."""
        from lc_request import Constants
        return self.request_status == Constants.STATUS_SYNCED
    
    def can_edit(self) -> bool:
        """Return True if this LC Request can be edited (draft or submitted only)."""
        return self.is_draft() or self.is_submitted()
    
    def can_sync_to_sap(self) -> bool:
        """Return True if this LC Request can be synced to SAP (submitted but not yet synced)."""
        return self.is_submitted() and not self.is_synced()
    
    def mark_as_synced(self, inward_no: str, lc_ref_no: str) -> None:
        """
        Mark this LC Request as synced to SAP with the returned reference numbers.
        
        Args:
            inward_no: Inward number returned by SAP
            lc_ref_no: LC reference number returned by SAP
        """
        from lc_request import Constants
        self.request_status = Constants.STATUS_SYNCED
        self.inward_no = inward_no
        self.lc_ref_no = lc_ref_no


class LcDetailsProxy(LcDetails):
    """
    Proxy model for LcDetails with business logic.
    
    Represents the detailed LC information extracted from OCR or entered manually.
    Tracks whether data was OCR-extracted (Y) or user-editable (N).
    """
    
    class Meta:
        proxy = True
    
    def is_ocr_extracted(self) -> bool:
        """Return True if this entry was created from OCR extraction (Y flag)."""
        return self.extracted_flag == 'Y'
    
    def is_user_editable(self) -> bool:
        """Return True if this entry is the user-editable version (N flag)."""
        return self.extracted_flag == 'N'
    
    def has_been_modified(self, ocr_entry: 'LcDetailsProxy') -> bool:
        """
        Check if this user-editable entry differs from the original OCR extraction.
        
        Args:
            ocr_entry: The Y-flagged LcDetails entry to compare against
            
        Returns:
            True if any field has been modified from the OCR version
        """
        from lc_request import Constants
        
        if not ocr_entry or not ocr_entry.is_ocr_extracted():
            return False
        
        for field in Constants.LC_DETAIL_FIELDS:
            if getattr(self, field, None) != getattr(ocr_entry, field, None):
                return True
        
        return False


class LcFilesProxy(LcFiles):
    """
    Proxy model for LcFiles with business logic.
    
    Represents file attachments (PDFs) associated with an LC Request.
    """
    
    objects = LCFileManager()
    
    class Meta:
        proxy = True
    
    def is_primary_document(self) -> bool:
        """Return True if this is the primary LC document (not an attachment)."""
        from lc_request import Constants
        return self.category == Constants.LC_DOCUMENT
    
    def is_attachment(self) -> bool:
        """Return True if this is an additional attachment."""
        from lc_request import Constants
        return self.category == Constants.LC_ATTACHMENT
    
    def is_active(self) -> bool:
        """Return True if this file is active (not deleted or archived)."""
        return self.status == 'active'
