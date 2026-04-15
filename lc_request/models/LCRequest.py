from django.db import models


class LCRequest(models.Model):

    STATUS_CHOICES = [
        ("draft",     "Draft"),
        ("submitted", "Submitted"),
    ]

    # LC Details — extracted by OCR, editable by user
    instrument_number                  = models.CharField(max_length=100, blank=True, null=True)
    form_of_doc                        = models.CharField(max_length=100, blank=True, null=True)
    opening_bank                       = models.CharField(max_length=255, blank=True, null=True)
    opening_date                       = models.DateField(blank=True, null=True)
    usance_period                      = models.IntegerField(blank=True, null=True)
    dispatch_upto_date                 = models.DateField(blank=True, null=True)
    negotiation_days                   = models.IntegerField(blank=True, null=True)
    expiry_date                        = models.DateField(blank=True, null=True)
    place_take_in_charge               = models.CharField(max_length=255, blank=True, null=True)
    place_of_final_destination         = models.CharField(max_length=255, blank=True, null=True)
    advising_bank                      = models.CharField(max_length=255, blank=True, null=True)
    es                                 = models.BooleanField(default=False, null=True, blank=True)
    et                                 = models.BooleanField(default=False, null=True, blank=True)
    er                                 = models.BooleanField(default=False, null=True, blank=True)
    grace_value                        = models.BigIntegerField(blank=True, null=True)
    percentage_credit_amount_tolerance = models.CharField(max_length=50, blank=True, null=True)
    cust_name_inv_print                = models.CharField(max_length=255, blank=True, null=True)
    customer_name                      = models.CharField(max_length=255, blank=True, null=True)
    clause_45a                         = models.TextField(blank=True, null=True)
    incoterm                           = models.CharField(max_length=100, blank=True, null=True)
    imps_remark                        = models.CharField(max_length=255, blank=True, null=True)
    additional_condition_46a           = models.TextField(blank=True, null=True)
    clause_78                          = models.TextField(blank=True, null=True)

    # Attachment
    attachment = models.FileField(upload_to="lc_attachments/", blank=True, null=True)
    password   = models.CharField(max_length=255, blank=True, null=True)

    # Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Audit
    created_by   = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lc_request"
        ordering = ["-created_date"]

    def __str__(self):
        return f"LC-{self.pk} | {self.instrument_number or 'N/A'} | {self.status}"