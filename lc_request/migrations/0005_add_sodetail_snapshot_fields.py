from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds the Masters snapshot columns to ``so_detail``.

    These columns were previously missing, which caused ``_save_so_details``
    in services.py to fail silently on write.  The three financial columns
    (interest_free_credit_days, interest_charges, usance_period) remain on
    ``lc_so_detail`` as designed — this migration only touches ``so_detail``.
    """

    dependencies = [
        ("lc_request", "0004_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sodetail",
            name="company_code",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="plant_code",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="customer_code",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="ship_to_party",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="so_value",
            field=models.DecimalField(
                max_digits=18, decimal_places=2, blank=True, null=True
            ),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="pyt_terms",
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="remarks",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="cust_reference",
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="cust_reference_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="inco_terms",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="inco_location",
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sodetail",
            name="so_status",
            field=models.CharField(max_length=50, blank=True, null=True),
        ),
        # Enforce one row per SO per LC Request
        migrations.AlterUniqueTogether(
            name="sodetail",
            unique_together={("lc_request", "so_number")},
        ),
    ]
