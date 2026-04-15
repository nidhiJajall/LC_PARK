from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LCRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instrument_number', models.CharField(blank=True, max_length=100, null=True)),
                ('form_of_doc', models.CharField(blank=True, max_length=100, null=True)),
                ('opening_bank', models.CharField(blank=True, max_length=255, null=True)),
                ('opening_date', models.DateField(blank=True, null=True)),
                ('usance_period', models.IntegerField(blank=True, null=True)),
                ('dispatch_upto_date', models.DateField(blank=True, null=True)),
                ('negotiation_days', models.IntegerField(blank=True, null=True)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('place_take_in_charge', models.CharField(blank=True, max_length=255, null=True)),
                ('place_of_final_destination', models.CharField(blank=True, max_length=255, null=True)),
                ('advising_bank', models.CharField(blank=True, max_length=255, null=True)),
                ('es', models.BooleanField(blank=True, default=False, null=True)),
                ('et', models.BooleanField(blank=True, default=False, null=True)),
                ('er', models.BooleanField(blank=True, default=False, null=True)),
                ('grace_value', models.BigIntegerField(blank=True, null=True)),
                ('percentage_credit_amount_tolerance', models.CharField(blank=True, max_length=50, null=True)),
                ('cust_name_inv_print', models.CharField(blank=True, max_length=255, null=True)),
                ('customer_name', models.CharField(blank=True, max_length=255, null=True)),
                ('clause_45a', models.TextField(blank=True, null=True)),
                ('incoterm', models.CharField(blank=True, max_length=100, null=True)),
                ('imps_remark', models.CharField(blank=True, max_length=255, null=True)),
                ('additional_condition_46a', models.TextField(blank=True, null=True)),
                ('clause_78', models.TextField(blank=True, null=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='lc_attachments/')),
                ('password', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted')], default='draft', max_length=20)),
                ('created_by', models.CharField(blank=True, max_length=100, null=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'lc_request', 'ordering': ['-created_date']},
        ),
        migrations.CreateModel(
            name='LCSODetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interest_free_credit_days', models.IntegerField(blank=True, null=True)),
                ('interest_charges', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('usance_period', models.IntegerField(blank=True, null=True)),
            ],
            options={'db_table': 'lc_so_detail'},
        ),
        migrations.CreateModel(
            name='SODetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('so_number', models.CharField(max_length=50)),
                ('lc_so_detail', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='so_detail', to='lc_request.lcsodetail')),
                ('lc_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='so_details', to='lc_request.lcrequest')),
            ],
            options={'db_table': 'so_detail'},
        ),
        migrations.AlterUniqueTogether(
            name='sodetail',
            unique_together={('lc_request', 'so_number')},
        ),
    ]