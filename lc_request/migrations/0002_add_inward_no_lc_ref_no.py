# Generated migration — add INWARD_NO and LC_REF_NO to TRANS_LC_REQUEST
# Run: python manage.py migrate lc_request

from django.db import migrations, models


class Migration(migrations.Migration):

    # Replace with the actual name of the last migration in this app.
    # You can find it with: python manage.py showmigrations lc_request
    dependencies = [
        ("lc_request", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lcrequest",
            name="inward_no",
            field=models.CharField(
                blank=True,
                db_column="INWARD_NO",
                help_text="Inward number returned by SAP after successful LC sync.",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="lcrequest",
            name="lc_ref_no",
            field=models.CharField(
                blank=True,
                db_column="LC_REF_NO",
                help_text="LC reference number (document number) returned by SAP after successful sync.",
                max_length=50,
                null=True,
            ),
        ),
    ]