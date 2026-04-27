from django.db import models
from reversion import revisions as reversion
from api.models import BaseModel
from lc_request import Constants


class LcDetails(BaseModel):
    lc_details_id = models.AutoField(db_column='LC_DETAILS_ID', primary_key=True)

    instrument_number = models.CharField(db_column='INSTRUMENT_NUMBER', max_length=100)

    form_of_doc = models.CharField(db_column='FORM_OF_DOC', max_length=100, blank=True, null=True)
    opening_bank = models.CharField(db_column='OPENING_BANK', max_length=200, blank=True, null=True)
    opening_date = models.DateField(db_column='OPENING_DATE', blank=True, null=True)
    unance_period = models.IntegerField(db_column='UNANCE_PERIOD', blank=True, null=True)
    dispatch_upto_date = models.DateField(db_column='DISPATCH_UPTO_DATE', blank=True, null=True)
    negotiation_days = models.IntegerField(db_column='NEGOTIATION_DAYS', blank=True, null=True)
    expiry_date = models.DateField(db_column='EXPIRY_DATE', blank=True, null=True)
    place_take_in_charge = models.CharField(db_column='PLACE_TAKE_IN_CHARGE', max_length=200, blank=True, null=True)
    place_of_final_destination = models.CharField(db_column='PLACE_OF_FINAL_DESTINATION', max_length=200, blank=True,
                                                  null=True)
    advising_bank = models.CharField(db_column='ADVISING_BANK', max_length=200, blank=True, null=True)
    es = models.CharField(db_column='ES', max_length=10, blank=True, null=True)
    et = models.CharField(db_column='ET', max_length=10, blank=True, null=True)
    er = models.CharField(db_column='ER', max_length=10, blank=True, null=True)
    grace_value = models.DecimalField(db_column='GRACE_VALUE', max_digits=15, decimal_places=2, blank=True, null=True)
    percentage_credit_amount_tolerance = models.TextField(db_column='PERCENTAGE_CREDIT_AMOUNT_TOLERANCE', max_length=20,
                                                          blank=True, null=True)
    cust_name_inv_print = models.CharField(db_column='CUST_NAME_INV_PRINT', max_length=200, blank=True, null=True)
    customer_name = models.CharField(db_column='CUSTOMER_NAME', max_length=200, blank=True, null=True)
    clause_45a = models.TextField(db_column='CLAUSE_45A', blank=True, null=True)
    incoterm = models.CharField(db_column='INCOTERM', max_length=10, blank=True, null=True)
    imps_remark = models.TextField(db_column='IMPS_REMARK', blank=True, null=True)
    additional_condition_46a = models.TextField(db_column='ADDITIONAL_CONDITION_46A', blank=True, null=True)
    clause_78 = models.TextField(db_column='CLAUSE_78', blank=True, null=True)

    extracted_flag = models.CharField(
        db_column='EXTRACTED_FLAG',
        max_length=1,
        choices=[('Y', 'Extracted'), ('N', 'User Editable')],
        default='N',
    )

    def __str__(self):
        return f"{self.instrument_number} [{self.extracted_flag}]"

    class Meta:
        db_table = 'TRANS_LC_DETAILS'
        app_label = Constants.APP_LABEL


reversion.register(LcDetails)