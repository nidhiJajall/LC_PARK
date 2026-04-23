"""
Sync SO Special Remarks from SAP OData API
"""
import traceback
import requests
import urllib3

import pandas as pd
from django.core.management import BaseCommand
from sqlalchemy import create_engine, text
from sqlalchemy.engine import url

from masters.logger import lcparkLogs

# ------------------------------------------------------------------
# Disable SSL warnings (internal SAP cert)
# ------------------------------------------------------------------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Postgres DB CONFIG
# ------------------------------------------------------------------
database_credentials_postgres = {
    'schema': 'public',
    'username': 'postgres',
    'password': 'admin',
    'host': 'localhost',
    'database_name': 'LC_PARK',
    'port': '5432'
}

database_type_postgres = 'postgres'


class Command(BaseCommand):
    """
    Sync SO Special Remarks from SAP API into MST_SODATA
    """

    # ------------------------------------------------------------------
    # SAP CONFIG
    # ------------------------------------------------------------------
    SAP_BASE_URL = (
        "https://vhnmwbadci.sap.myamns.in:44300/sap/opu/odata/sap/"
        "API_SALES_SCHEDULING_AGREEMENT/"
        "A_SalesSchedgAgrmtText("
        "SalesSchedulingAgreement='{so_no}',"
        "Language='EN',"
        "LongTextID='ES22'"
        ")"
    )

    SAP_AUTH_HEADER = {
        "Accept": "application/json",
        "Authorization": "Basic YWJhcF90ZXN0OkFiYXBlcnNAMTUwYWJhcA=="
    }

    SAP_CLIENT = "150"

    # ------------------------------------------------------------------
    # DB connection (unchanged pattern)
    # ------------------------------------------------------------------
    def db_connection(self, database_creds, database_type):
        try:
            global engine_bf

            if database_type == 'postgres':
                engine_bf = create_engine(
                    'postgresql://%s:%s@%s:%s/%s' % (
                        database_creds['username'],
                        database_creds['password'],
                        database_creds['host'],
                        database_creds['port'],
                        database_creds['database_name'],
                    ),
                    connect_args={'options': '-csearch_path=%s'
                                  % database_creds['schema']}
                )
                lcparkLogs.info(
                    "Initializing postgres Database connection --> %s:%s" %
                    (database_creds['host'], database_creds['port'])
                )
            else:
                raise Exception("Only postgres supported in this sync")

            conn = engine_bf.connect()
            return conn, engine_bf

        except Exception as ex:
            lcparkLogs.error(f'Database connection failed --> {ex}')
            raise ex

    # ------------------------------------------------------------------
    # SAP API CALL
    # ------------------------------------------------------------------
    def fetch_special_remark(self, so_number):
        try:
            so_number = str(so_number).zfill(10)

            url = (
                f"{self.SAP_BASE_URL.format(so_no=so_number)}"
                f"?sap-client={self.SAP_CLIENT}&$format=json"
            )

            response = requests.get(
                url,
                headers=self.SAP_AUTH_HEADER,
                verify=False,
                timeout=5
            )

            if response.status_code == 200:
                return response.json().get('d', {}).get('LongText')

            lcparkLogs.warning(
                f"SAP API failed for SO {so_number} "
                f"Status {response.status_code}"
            )
            return None

        except Exception as ex:
            lcparkLogs.error(
                f"SAP API exception for SO {so_number} --> {ex}"
            )
            return None

    # ------------------------------------------------------------------
    # MAIN INSERT LOGIC (mirrors sample)
    # ------------------------------------------------------------------
    def insert_data(self):
        try:
            lcparkLogs.info("CONNECTING POSTGRES DB")

            conn_postgres, engine_postgres = \
                self.db_connection(
                    database_credentials_postgres,
                    database_type_postgres
                )

            # ----------------------------------------------------------
            # Fetch SO numbers needing remarks
            # ----------------------------------------------------------
            so_df = pd.read_sql(
                """
                SELECT "SO_NUMBER"
                FROM "MST_SODATA"
                WHERE "REMARKS" IS NULL OR "REMARKS" = ''
                """,
                con=conn_postgres
            )

            if so_df.empty:
                lcparkLogs.info("No SOs pending for remarks update")
                return

            lcparkLogs.info(
                f"Fetching remarks for {len(so_df)} SO numbers"
            )

            # ----------------------------------------------------------
            # API LOOP (same logic you validated)
            # ----------------------------------------------------------
            remarks = []
            for idx, so in enumerate(so_df['SO_NUMBER'], 1):
                lcparkLogs.info(
                    f"[{idx}/{len(so_df)}] Fetching SO {so}"
                )
                remarks.append(self.fetch_special_remark(so))

            so_df['REMARKS'] = remarks
            so_df.dropna(subset=['REMARKS'], inplace=True)

            # ----------------------------------------------------------
            # Update Postgres
            # ----------------------------------------------------------
            with engine_postgres.begin() as conn:
                conn.execute(text("""
                    UPDATE "MST_SODATA"
                    SET "REMARKS" = src."REMARKS"
                    FROM (VALUES (:so, :remark)) 
                    AS src("SO_NUMBER", "REMARKS")
                    WHERE "MST_SODATA"."SO_NUMBER" = src."SO_NUMBER"
                """), [
                    {
                        "so": row.SO_NUMBER,
                        "remark": row.REMARKS
                    }
                    for row in so_df.itertuples(index=False)
                ])

            lcparkLogs.info(
                f"Successfully updated {len(so_df)} SO remarks"
            )

        except Exception as ex:
            lcparkLogs.error(
                "EXCEPTION OCCURRED WHILE SYNCING SAP REMARKS"
            )
            lcparkLogs.error(ex)
            lcparkLogs.error(traceback.format_exc())

    # ------------------------------------------------------------------
    # Django entry
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.insert_data()