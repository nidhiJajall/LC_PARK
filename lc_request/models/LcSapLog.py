"""
LcSapLog model — stores SAP sync attempt payload and response for each LC Request.

One row is created per sync attempt (success or failure).
"""
import logging

from django.db import models
from reversion import revisions as reversion

from api.models import BaseModel
from lc_request import Constants

logger = logging.getLogger(__name__)


class LcSapLog(BaseModel):
    """
    Audit log for every SAP sync attempt on an LC Request.

    Fields
    ------
    lc_request  : FK to the LcRequest that was synced.
    payload     : JSON payload that was sent to SAP (stored as JSONField).
    response    : JSON response received from SAP (stored as JSONField).
    http_status : HTTP status code returned by SAP (e.g. 200, 201, 400, 502).
    success     : True if SAP returned 200/201, False otherwise.
    synced_by   : Username of the user who triggered the sync.
    """

    lc_request = models.ForeignKey(
        "lc_request.LcRequest",
        db_column="LC_REQUEST_ID",
        on_delete=models.CASCADE,
        related_name="sap_logs",
        help_text="The LC Request that was synced to SAP.",
    )

    payload = models.JSONField(
        db_column="PAYLOAD",
        help_text="SAP OData payload sent during sync.",
    )

    response = models.JSONField(
        db_column="RESPONSE",
        null=True,
        blank=True,
        help_text="SAP OData response received after sync.",
    )

    http_status = models.IntegerField(
        db_column="HTTP_STATUS",
        null=True,
        blank=True,
        help_text="HTTP status code from SAP (200, 201, 400, 502, …).",
    )

    success = models.BooleanField(
        db_column="SUCCESS",
        default=False,
        help_text="True if SAP returned a 200/201 response.",
    )

    synced_by = models.CharField(
        db_column="SYNCED_BY",
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the operator who triggered the sync.",
    )

    def __str__(self):
        return (
            f"SapLog LC#{self.lc_request_id} "
            f"{'✓' if self.success else '✗'} "
            f"[{self.http_status}] "
            f"@ {self.created_date}"
        )

    class Meta:
        db_table  = "TRANS_LC_SAP_LOG"
        app_label = Constants.APP_LABEL
        ordering  = ["-created_date"]


reversion.register(LcSapLog)