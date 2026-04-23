from django.db import models
from api.models import BaseModel
from api.alias import AliasField
from reversion import revisions as reversion


class Sodata(BaseModel):
    so_id = models.AutoField(primary_key=True, db_column='SO_ID')

    so_number = models.CharField(db_column='SO_NUMBER', max_length=20, db_index=True, null=True)
    company_code = models.CharField(db_column='COMPANY_CODE', max_length=10)
    plant_code = models.CharField(db_column='PLANT_CODE', max_length=10)
    customer_code = models.CharField(db_column='CUSTOMER_CODE', max_length=20)  # Added (from your table image)
    ship_to_party = models.CharField(db_column='SHIP_TO_PARTY', max_length=20)
    ship_to_address = models.CharField(db_column='SHIP_TO_ADDRESS', max_length=100, null=True, blank=True)
    ship_to_city = models.CharField(db_column='SHIP_TO_CITY', max_length=50, null=True, blank=True)
    ship_to_street = models.CharField(db_column='SHIP_TO_STREET', max_length=50, null=True, blank=True)
    ship_to_pincode = models.CharField(db_column='SHIP_TO_PINCODE', max_length=50, null=True, blank=True)
    ship_to_country = models.CharField(db_column='SHIP_TO_COUNTRY', max_length=50, null=True, blank=True)

    so_value = models.DecimalField(db_column='SO_VALUE', max_digits=18, decimal_places=2)

    pyt_terms = models.CharField(db_column='PYT_TERMS', max_length=50)
    remarks = models.CharField(db_column='REMARKS', max_length=200)
    cust_reference = models.CharField(db_column='CUST_REFERENCE', max_length=50)

    cust_reference_date = models.DateField(db_column='CUST_REFERENCE_DATE')

    inco_terms = models.CharField(db_column='INCO_TERMS', max_length=30)
    inco_location = models.CharField(db_column='INCO_LOCATION', max_length=100)

    status = models.CharField(db_column='STATUS', max_length=80, default='Active')
    name = AliasField(db_column='COMPANY_CODE', blank=True, null=True)

    class UI_Meta:
        ui_specs = {
            "listview": [
                "this value"
            ],
            "formview": [
                {
                    "sectionlabel": "SO Details",
                    "cols": 2,
                    "colComponent": [
                        {
                            "label": "Company Code",
                            "decorator": "company_code",
                            "type": "textbox",
                            "required": "true",
                            "message": "Company Code is required.",
                            "id": "company_code",
                            "placeholder": "Enter Company Code",
                            "disabled": False
                        },
                        {
                            "label": "Plant Code",
                            "decorator": "plant_code",
                            "type": "textbox",
                            "required": "true",
                            "message": "Plant Code is required.",
                            "id": "plant_code",
                            "placeholder": "Enter Plant Code",
                            "disabled": False
                        },
                        {
                            "label": "Customer Code",
                            "decorator": "customer_code",
                            "type": "textbox",
                            "required": "true",
                            "message": "Customer Code is required.",
                            "id": "customer_code",
                            "placeholder": "Enter Customer Code",
                            "disabled": False
                        },
                        {
                            "label": "Ship To Party",
                            "decorator": "ship_to_party",
                            "type": "textbox",
                            "required": "true",
                            "message": "Ship To Party is required.",
                            "id": "ship_to_party",
                            "placeholder": "Enter Ship To Party",
                            "disabled": False
                        },
                        {
                            "label": "Ship To Address",
                            "decorator": "ship_to_address",
                            "type": "textbox",
                            "required": "true",
                            "message": "Ship To Address is required.",
                            "id": "ship_to_address",
                            "placeholder": "Enter Ship To Address"
                        },
                        {
                            "label": "Ship To City",
                            "decorator": "ship_to_city",
                            "type": "textbox",
                            "required": "true",
                            "message": "Ship To City is required.",
                            "id": "ship_to_city",
                            "placeholder": "Enter Ship To City",
                            "disabled": False
                        },
                        {
                            "label": "Ship To Street",
                            "decorator": "ship_to_street",
                            "type": "textbox",
                            "required": "true",
                            "message": "Ship To Street is required.",
                            "id": "ship_to_street",
                            "placeholder": "Enter Ship To Street"
                        },
                        {
                            "label": "Ship To Pincode",
                            "decorator": "ship_to_pincode",
                            "type": "textbox",
                            "required": "true",
                            "message": "Ship To Pincode is required.",
                            "id": "ship_to_pincode",
                            "placeholder": "Enter Ship To Pincode",
                            "disabled": False
                        },
                        {
                            "label": "Ship To Country",
                            "decorator": "ship_to_country",
                            "type": "textbox",
                            "required": "true",
                            "message": "Ship To Country is required.",
                            "id": "ship_to_country",
                            "placeholder": "Enter Ship To Country"
                        },
                        {
                            "label": "SO Value",
                            "decorator": "so_value",
                            "type": "textbox",
                            "required": "true",
                            "message": "Enter SO Value",
                            "id": "so_value",
                            "placeholder": "Enter SO Value (e.g., 125000.00)",
                            "disabled": False
                        },
                        {
                            "label": "Pyt Terms",
                            "decorator": "pyt_terms",
                            "type": "textbox",
                            "required": "true",
                            "message": "Payment Terms are required.",
                            "id": "pyt_terms",
                            "placeholder": "Enter Payment Terms",
                            "disabled": False
                        },
                        {
                            "label": "Special Remark - Sales Contract",
                            "decorator": "remarks",
                            "type": "textbox",
                            "required": "false",
                            "message": "Enter Remarks",
                            "id": "remarks",
                            "placeholder": "Enter Special Remarks (optional)",
                            "disabled": False,
                            "maxlength": 200
                        },
                        {
                            "label": "Cust. Reference / PO number",
                            "decorator": "cust_reference",
                            "type": "textbox",
                            "required": "true",
                            "message": "Customer Reference / PO number is required.",
                            "id": "cust_reference",
                            "placeholder": "Enter Customer Reference / PO number",
                            "disabled": False
                        },
                        {
                            "label": "Cust. Ref. Date / PO Date",
                            "decorator": "cust_reference_date",
                            "required": "true",
                            "message": "Please select the date.",
                            "placeholder": "Select Date",
                            "type": "date",
                            "id": "cust_reference_date",
                            "dateFormatList": "YYYY-MM-DD",
                            "disabled": False
                        },
                        {
                            "label": "INCO terms",
                            "decorator": "inco_terms",
                            "type": "textbox",
                            "required": "true",
                            "message": "INCO terms are required.",
                            "id": "inco_terms",
                            "placeholder": "Enter INCO terms (e.g., FOB/CIF/DDP)",
                            "disabled": False
                        },
                        {
                            "label": "INCO Location",
                            "decorator": "inco_location",
                            "type": "textbox",
                            "required": "true",
                            "message": "INCO Location is required.",
                            "id": "inco_location",
                            "placeholder": "Enter INCO Location",
                            "disabled": False
                        },

                        # ---- Mandatory audit fields in UI (disabled) ----
                        {
                            "label": "Created By",
                            "decorator": "created_by",
                            "type": "textbox",
                            "required": "true",
                            "message": "Created By!",
                            "id": "created_by",
                            "placeholder": "Created By",
                            "disabled": True
                        },
                        {
                            "label": "Created Date",
                            "decorator": "created_date",
                            "required": "true",
                            "message": "Created Date",
                            "placeholder": "Select Date",
                            "type": "date",
                            "id": "created_date",
                            "dateFormatList": "YYYY-MM-DD HH:mm:ss",
                            "disabled": True
                        },
                        {
                            "label": "Updated By",
                            "decorator": "last_updated_by",
                            "type": "textbox",
                            "required": "true",
                            "message": "Last Updated By!",
                            "id": "last_updated_by",
                            "placeholder": "Last Updated By",
                            "disabled": True
                        },
                        {
                            "label": "Last Updated",
                            "decorator": "last_updated_date",
                            "required": "true",
                            "message": "Last Updated Date",
                            "placeholder": "Select Date",
                            "type": "date",
                            "id": "last_updated_date",
                            "dateFormatList": "YYYY-MM-DD HH:mm:ss",
                            "disabled": True
                        }
                    ]
                }
            ]
        }

    class Meta:
        db_table = 'MST_SODATA'
        app_label = 'masters'


reversion.register(Sodata)