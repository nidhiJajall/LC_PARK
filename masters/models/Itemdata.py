from django.db import models
from api.models import BaseModel
from api.alias import AliasField
from reversion import revisions as reversion


class Itemdata(BaseModel):
    item_id = models.AutoField(primary_key=True, db_column='SO_ID')

    so_number = models.CharField(db_column='SO_NUMBER', max_length=20, blank=True, null=True)
    item_number = models.CharField(db_column='ITEM_NUMBER', max_length=10)
    material_no = models.CharField(db_column='MATERIAL_NO', max_length=10)
    material_qty = models.CharField(db_column='MATERIAL_QTY', max_length=20)  # Added (from your table image)
    unit = models.CharField(db_column='UNIT', max_length=20)
    material_price = models.CharField(db_column='MATERIAL_PRICE', max_length=20)
    matl_value = models.CharField(db_column='MATL_VALUE', max_length=20)

    status = models.CharField(db_column='STATUS', max_length=80, default='Active')
    name = AliasField(db_column='COMPANY_CODE', blank=True, null=True)

    class UI_Meta:
        ui_specs = {
            "listview": [
                "this value"
            ],
            "formview": [
                {
                    "sectionlabel": "ITEM-LEVEL SO DATA",
                    "cols": 2,
                    "colComponent": [
                        {
                            "label": "Item Number",
                            "decorator": "item_number",
                            "type": "textbox",
                            "required": "true",
                            "message": "Item Number is required.",
                            "id": "item_number",
                            "placeholder": "Enter Item Number",
                            "disabled": False
                        },
                        {
                            "label": "Material No.",
                            "decorator": "material_no",
                            "type": "textbox",
                            "required": "true",
                            "message": "Material No. is required.",
                            "id": "material_no",
                            "placeholder": "Enter Material No.",
                            "disabled": False
                        },
                        {
                            "label": "Material Qty",
                            "decorator": "material_qty",
                            "type": "textbox",
                            "required": "true",
                            "message": "Material Qty is required.",
                            "id": "material_qty",
                            "placeholder": "Enter Material Qty",
                            "disabled": False
                        },
                        {
                            "label": "Unit",
                            "decorator": "unit",
                            "type": "textbox",
                            "required": "true",
                            "message": "Unit is required.",
                            "id": "unit",
                            "placeholder": "Enter Unit",
                            "disabled": False
                        },
                        {
                            "label": "Material Price",
                            "decorator": "material_price",
                            "type": "textbox",
                            "required": "true",
                            "message": "Enter Material Price",
                            "id": "material_price",
                            "placeholder": "Enter Material Price",
                            "disabled": False
                        },
                        {
                            "label": "matl_value",
                            "decorator": "matl_value",
                            "type": "textbox",
                            "required": "true",
                            "message": "Material Value are required.",
                            "id": "matl_value",
                            "placeholder": "Enter Material Value",
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
        db_table = 'MST_ITEM_DATA'
        app_label = 'masters'


reversion.register(Itemdata)