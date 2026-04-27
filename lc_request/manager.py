"""
Custom model managers for the LC app.
Mirrors fi_vendor/manager.py pattern.
"""
from commons.manager import BaseManager


class LCFileManager(BaseManager):
    """
    Manager for LCFiles model.
    Provides filtered querysets scoped to an LC Request.
    """

    def get_by_lc_request(self, lc_request_id: int, category: str = None):
        """
        Return active files for a given LC Request, optionally filtered by category.

        Args:
            lc_request_id: PK of the parent LCRequest.
            category:       Optional file category (e.g. 'LC_DOCUMENT').

        Returns:
            Filtered queryset of LCFiles.
        """
        qs = self.filter(
            is_active=True,
            is_deleted=False,
            lc_request_id=lc_request_id,
        )
        if category:
            qs = qs.filter(category=category)
        return qs
