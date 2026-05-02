from django.core.management.base import BaseCommand
from masters.models import Itemdata
from django.db import transaction
from pathlib import Path
import pandas as pd


class Command(BaseCommand):
    help = "Import SO item-level data into SQLite from VBAP"

    def handle(self, *args, **kwargs):
        base_dir = Path("data")

        # ✅ Read Excel — VBAP is the only source for item data
        df_vbap = pd.read_excel(base_dir / "VBAP.xlsx", engine="openpyxl")

        # ✅ Normalize headers
        df_vbap.columns = df_vbap.columns.str.strip()

        # ---------------- Helper functions ---------------- #

        def txt(val):
            return "" if pd.isna(val) else str(val).strip()

        def num(val, default=0):
            if pd.isna(val):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        self.stdout.write(f"Total item records: {len(df_vbap)}")

        # ✅ Insert every VBAP row — one row per SO line item
        with transaction.atomic():
            for _, row in df_vbap.iterrows():
                so_number   = txt(row["Sales document"])
                item_number = txt(row["Sales Document Item"])

                Itemdata.objects.update_or_create(
                    so_number=so_number,
                    item_number=item_number,
                    defaults={
                        # ✅ VBAP (Item-level)
                        "material_no":    txt(row.get("Material")),
                        "material_qty":   txt(row.get("Order Quantity")),
                        "unit":           txt(row.get("Sales unit")),
                        "material_price": txt(row.get("Net Price")),
                        "matl_value":     txt(row.get("Net Value")),

                        "status": "Active",
                    }
                )

        self.stdout.write(
            self.style.SUCCESS("✅ ITEM DATA SUCCESSFULLY INSERTED INTO SQLITE")
        )