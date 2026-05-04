"""
Custom model managers for the lc_request app.
Mirrors commons/manager.py BaseManager pattern.
"""
from commons.manager import BaseManager


class LCFileManager(BaseManager):
    """Manager for LcFiles — provides querysets scoped to an LC Request."""

    def get_by_lc_request(self, lc_request_id: int, category: str = None):
        """
        Return active, non-deleted files for a given LcRequest PK.
        Optionally filter by file category (e.g. 'LC_DOCUMENT').
        """
        qs = self.filter(
            is_active=True,
            is_deleted=False,
            lc_request_id=lc_request_id,
        )
        if category:
            qs = qs.filter(category=category)
        return qs