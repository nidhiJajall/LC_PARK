# lc_request/models/LCSODetail.py

from django.db import models
from .LCRequest import LCRequest


class LCSODetail(models.Model):
    """
    Child rows — one per SO Number the user adds dynamically in the form.
    Linked to LCRequest via FK.
    """

    lc_request = models.ForeignKey(
        LCRequest,
        on_delete=models.CASCADE,
        related_name="so_details"
    )

    so_number                 = models.CharField(max_length=50)
    interest_free_credit_days = models.IntegerField(blank=True, null=True)
    interest_charges          = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    usance_period             = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "lc_so_detail"

    def __str__(self):
        return f"SO {self.so_number} → LC-{self.lc_request_id}"
