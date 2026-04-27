from django.db import models
from reversion import revisions as reversion
from api.models import BaseModel
from lc_request import Constants
from lc_request.models.LcDetails import LcDetails
from masters.models.Sodata import Sodata


class LcRequest(BaseModel):
    lc_details = models.ForeignKey(
        LcDetails,
        db_column='LC_DETAILS_ID',
        on_delete=models.CASCADE,
        related_name='lc_request_lc_details',
        null=True,
        blank=True,
        help_text="Points to the N (user-editable) LcDetails entry.",
    )

    interest_free_credit_days = models.IntegerField(db_column='INTEREST_FREE_CREDIT_DAYS', blank=True, null=True)
    interest_charges = models.DecimalField(db_column='INTEREST_CHARGES', max_digits=12, decimal_places=2, blank=True,
                                           null=True)
    usance_period = models.IntegerField(db_column='USANCE_PERIOD', blank=True, null=True)

    # M2M: table name will be TRANS_LC_REQUEST_so_data
    so_data = models.ManyToManyField(Sodata, related_name='lc_request_sodata', blank=True)

    request_status = models.CharField(
        db_column='REQUEST_STATUS',
        max_length=20,
        default=Constants.STATUS_DRAFT,
        choices=Constants.STATUS_CHOICES,
    )

    def __str__(self):
        return f"LCRequest #{self.pk}"

    class Meta:
        app_label = Constants.APP_LABEL
        db_table = 'TRANS_LC_REQUEST'


reversion.register(LcRequest)