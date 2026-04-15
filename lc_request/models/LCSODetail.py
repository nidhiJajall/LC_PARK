from django.db import models


class LCSODetail(models.Model):
    # User-entered financial data per SO
    interest_free_credit_days = models.IntegerField(blank=True, null=True)
    interest_charges          = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    usance_period             = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "lc_so_detail"

    def __str__(self):
        return f"LCSODetail-{self.pk}"