# lc_request/models/SODetail.py
# ─────────────────────────────────────────────────────────────────────────────
# SODetail is the "bridge" table between LCRequest and LCSODetail.
#
# Three-table relationship:
#
#   LCRequest  ──< SODetail >── LCSODetail
#                   (FK)         (OneToOne)
#
#   LCRequest  : LC header (OCR fields, status, audit).
#   SODetail   : One row per SO attached to the LC.  Holds the Masters
#                snapshot columns (frozen at the time of entry) and a FK
#                back to the parent LCRequest.
#   LCSODetail : User-entered financial fields for that SO
#                (interest_free_credit_days, interest_charges, usance_period).
#                Kept separate so financial data can be updated independently
#                of the immutable Masters snapshot without touching SODetail.
#
# WHY keep three tables instead of one flat table?
#   Separation of concerns:
#     • SODetail snapshot = "what the Masters said when the LC was raised"
#       (write-once, auditable).
#     • LCSODetail = "what the LC team entered" (editable, versioned).
#   Splitting them makes it easy to re-fetch fresh Master data into a new
#   SODetail without overwriting the user's financial entries.
# ─────────────────────────────────────────────────────────────────────────────

from django.db import models


class SODetail(models.Model):
    """
    One row per SO number linked to a parent ``LCRequest``.

    The ``lc_request`` FK carries ``related_name="so_details"`` so the
    serialiser can reach these rows via
    ``lc_request_instance.so_details.all()`` without an explicit JOIN.

    The ``lc_so_detail`` OneToOne link is nullable so a ``SODetail`` row
    can be created before the LC team has entered any financial data.
    """

    lc_request = models.ForeignKey(
        "LCRequest",
        on_delete=models.CASCADE,
        related_name="so_details",
        db_index=True,
    )

    lc_so_detail = models.OneToOneField(
        "LCSODetail",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="so_detail",
    )

    # ── SO identity ───────────────────────────────────────────────────────────
    so_number = models.CharField(max_length=50)

    # ── Masters snapshot (intentionally denormalised) ─────────────────────────
    # WHY store a snapshot here instead of JOIN-ing Masters at read time?
    #   Masters data can change after the LC is raised (e.g. SO value revised).
    #   Snapshotting freezes the values as they were when the user raised the
    #   request, which is what auditors and banks need.
    company_code        = models.CharField(max_length=50,  blank=True, null=True)
    plant_code          = models.CharField(max_length=50,  blank=True, null=True)
    customer_code       = models.CharField(max_length=50,  blank=True, null=True)
    ship_to_party       = models.CharField(max_length=50,  blank=True, null=True)
    so_value            = models.DecimalField(
                              max_digits=18, decimal_places=2, blank=True, null=True
                          )
    pyt_terms           = models.CharField(max_length=100, blank=True, null=True)
    remarks             = models.TextField(blank=True, null=True)
    cust_reference      = models.CharField(max_length=100, blank=True, null=True)
    cust_reference_date = models.DateField(blank=True, null=True)
    inco_terms          = models.CharField(max_length=50,  blank=True, null=True)
    inco_location       = models.CharField(max_length=255, blank=True, null=True)
    so_status           = models.CharField(max_length=50,  blank=True, null=True)

    class Meta:
        db_table        = "so_detail"
        unique_together = [("lc_request", "so_number")]

    def __str__(self) -> str:
        return f"SO {self.so_number} → LC-{self.lc_request_id}"