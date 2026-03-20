# lc_request/models/LCRequest.py

from django.db import models


class LCRequest(models.Model):

    STATUS_CHOICES = [
        ("draft",     "Draft"),
        ("submitted", "Submitted"),
    ]

    # Auto-captured from SO lookup
    company_code       = models.CharField(max_length=50,  blank=True, null=True)
    plant_code         = models.CharField(max_length=50,  blank=True, null=True)
    customer_code      = models.CharField(max_length=50,  blank=True, null=True)
    ship_to_party      = models.CharField(max_length=100, blank=True, null=True)
    so_value           = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    payment_terms      = models.CharField(max_length=100, blank=True, null=True)
    special_remark     = models.CharField(max_length=255, blank=True, null=True)
    cust_ref_po_number = models.CharField(max_length=100, blank=True, null=True)
    cust_ref_po_date   = models.DateField(blank=True, null=True)

    # User inputs
    attachment         = models.FileField(upload_to="lc_attachments/", blank=True, null=True)
    password           = models.CharField(max_length=255, blank=True, null=True)
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Audit
    created_by         = models.CharField(max_length=100, blank=True, null=True)
    created_date       = models.DateTimeField(auto_now_add=True)
    updated_date       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "lc_request"
        ordering = ["-created_date"]

    def __str__(self):
        return f"LC-{self.pk} | {self.customer_code} | {self.status}"
