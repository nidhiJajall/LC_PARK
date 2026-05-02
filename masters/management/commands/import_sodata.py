from django.core.management.base import BaseCommand
from masters.models import Sodata
from django.db import transaction
from pathlib import Path
import pandas as pd
from datetime import date


class Command(BaseCommand):
    help = "Import SO master data into SQLite"

    def handle(self, *args, **kwargs):
        base_dir = Path("data")

        # ✅ Read Excel
        df_vbak = pd.read_excel(base_dir / "VBAK.xlsx", engine="openpyxl")
        df_vbkd = pd.read_excel(base_dir / "VBKD.xlsx", engine="openpyxl")
        df_vbap = pd.read_excel(base_dir / "VBAP.xlsx", engine="openpyxl")

        # ✅ Normalize headers
        for df in (df_vbak, df_vbkd, df_vbap):
            df.columns = df.columns.str.strip()

        # ✅ Pick ONE item per SO from VBAP
        df_vbap_min = (
            df_vbap
            .sort_values("Sales Document Item")
            .groupby("Sales document", as_index=False)
            .first()
        )

        # ✅ Merge (VBAK is master)
        df = (
            df_vbak
            .merge(df_vbkd, on="Sales document", how="left", suffixes=("", "_vbkd"))
            .merge(df_vbap_min, on="Sales document", how="left", suffixes=("", "_vbap"))
        )

        # ---------------- Helper functions ---------------- #

        def txt(val):
            return "" if pd.isna(val) else str(val).strip()

        def date_val(val):
            if pd.isna(val):
                return date(1900, 1, 1)
            if hasattr(val, "date"):
                return val.date()
            return val

        self.stdout.write(f"Total SO records: {len(df)}")

        # ✅ Insert into SQLITE
        with transaction.atomic(using="sqlite"):
            for _, row in df.iterrows():
                so_number = txt(row["Sales document"])

                Sodata.objects.using("sqlite").update_or_create(
                    so_number=so_number,
                    defaults={
                        "so_number": so_number,

                        # ✅ VBAK (Header)
                        # NOTE: VBAK does NOT have Company Code (BUKRS) in your file
                        "company_code": txt(row.get("Sales Organization")),
                        "customer_code": txt(row.get("Sold-to Party")),
                        "so_value": row["Net Value"] if not pd.isna(row["Net Value"]) else 0,

                        # ✅ VBAP (Item → header derived)
                        "plant_code": txt(row.get("Plant")),
                        "ship_to_party": txt(row.get("Ship-to Party")),

                        # ✅ VBKD (Business data)
                        "pyt_terms": txt(row.get("Payment terms")),
                        "cust_reference": txt(row.get("Customer Reference")),
                        "cust_reference_date": date_val(
                            row.get("Customer Ref. Date")
                        ),
                        "inco_terms": txt(row.get("Incoterms")),
                        "inco_location": txt(row.get("Incoterms Location 1")),

                        "ship_to_address": txt(row.get("Incoterms Location 1")),
                        "ship_to_city": txt(row.get("Incoterms Location 6") or "sample city"),
                        "ship_to_street": txt(row.get("Incoterms Location 3") or "sample street"),
                        "ship_to_pincode": txt(row.get("Incoterms Location 4") or "000000"),
                        "ship_to_country": txt(row.get("Incoterms Location 5") or "IN"),
                        "remarks": txt(row.get("Remarks") or "sample remarks"),
                        "status": "Active",
                    }
                )

        self.stdout.write(
            self.style.SUCCESS("✅ SO MASTER DATA SUCCESSFULLY INSERTED INTO SQLITE")
        )