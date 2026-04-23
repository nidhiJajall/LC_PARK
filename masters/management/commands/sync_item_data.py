"""
Sync Employee Data
"""
import traceback

import pandas as pd
from commons.mail_utils import render_html_message_simple
from django.core.management import BaseCommand
from email_amns import PublishMail
from sqlalchemy import create_engine, text
from sqlalchemy.engine import url

from masters.logger import lcparkLogs
# from my_secrets import secrets

# Connection string for oracle db
database_credentials_oracle = {
    'username': 'DS_TABLEAU_L1SUPP',
    'password': 'd5pr6s41su9p',
    'host': '10.165.1.21',
    'port': '1542',
    'service_name': 'DSPRDS4'
}

database_type_oracle = 'oracle'

# connection string for postgres db
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
    To insert employee data
    """

    # Connection function
    def db_connection(self, database_creds, database_type):
        """
        Creates Database connections for data insertion and update
        :return: Needed objects for database operations
        :rtype: SqlConnection, Session, Metadata, Table
        """
        try:
            global engine_bf

            if database_type == 'oracle':
                try:
                    connect_url = url.URL.create(
                        'oracle',
                        username=database_creds['username'],
                        password=database_creds['password'],
                        host=database_creds['host'],
                        port=database_creds['port'],
                        query=dict(service_name=database_creds['service_name'])
                    )
                    lcparkLogs.info("Initializing oracle Database connection --> %s:%s" %
                                           (database_creds['host'], database_creds['port']))
                    engine_bf = create_engine(connect_url)
                except Exception as ex:
                    lcparkLogs.error(f"Oracle Connection Error -->  Exception --> {ex}")
            elif database_type == 'postgres':
                try:
                    engine_bf = create_engine('postgresql://%s:%s@%s:%s/%s' % (
                        database_creds['username'],
                        database_creds['password'],
                        database_creds['host'],
                        database_creds['port'],
                        database_creds['database_name'],
                    ), connect_args={'options': '-csearch_path=%s' % database_creds['schema']})
                    lcparkLogs.info("Initializing postgres Database connection --> %s:%s" %
                                           (database_creds['host'], database_creds['port']))
                except Exception as ex:
                    lcparkLogs.error(f"Postgres Connection Error  --> {ex}")
            else:
                lcparkLogs.error(f"Invalid Database Type mentioned {database_type}. "
                                        f"Allowed types --> (oracle, postgres)")
                return "Invalid Database Type mentioned. Allowed types --> (oracle, postgres)"

            conn = engine_bf.connect()
            return conn, engine_bf
        except Exception as ex:
            lcparkLogs.error(f'Did not insert data --> Error --> {ex}')
            raise ex

    def insert_data(self):
        """
        insert data
        """
        global data_df
        try:
            try:
                lcparkLogs.info(f"CONNECTING ORACLE DB")
                conn_oracle, engine_oracle = \
                    self.db_connection(database_credentials_oracle, database_type_oracle)
                lcparkLogs.info(f"ORACLE Connection String : {conn_oracle}")

                lcparkLogs.info(f"CONNECTING POSTGRES DB")
                conn_postgres, engine_postgres = \
                    self.db_connection(database_credentials_postgres, database_type_postgres)
                lcparkLogs.info(f"Postgres Connection String : {conn_postgres}")

                lcparkLogs.info(f"INSERTING DATA IN POSTGRES DB")

                # AND(md.LABST > 0
                # OR
                # md.INSME > 0
                # OR
                # md.EINME > 0
                # OR
                # md.SPEME > 0)

                data_df = pd.read_sql("""SELECT
                                                vbap.vbeln AS so_number,
                                                vbap.posnr AS item_number,
                                                vbap.matnr AS material_no,
                                                vbap.kwmeng AS material_qty,
                                                vbap.vrkme AS unit,
                                                vbap.cmpre AS material_price,
                                                (vbap.kwmeng / NULLIF(vbap.kpein, 0)) 
                                                    * vbap.cmpre AS matl_value
                                            FROM DS_SAP.VBAP vbap
                                            JOIN DS_SAP.VBAK vbak
                                                ON vbap.vbeln = vbak.vbeln
                                            WHERE vbap.vbeln IS NOT NULL""", con=conn_oracle)
                data_df = data_df.rename(columns=str.upper)
                data_df.replace({pd.NaT: None}, inplace=True)
                lcparkLogs.info(f'Length of data : -- {len(data_df)}')

                conn_postgres.execute(text('TRUNCATE TABLE "MST_ITEM_DATA"'))
                # data_df.to_sql('MST_ITEM_DATA', con=conn_postgres, index=False, if_exists='append')
                data_df.to_sql(
                    'MST_ITEM_DATA',
                    con=conn_postgres,
                    index=False,
                    if_exists='append',
                    chunksize=100,
                    method='multi'
                )
                conn_postgres.commit()
                lcparkLogs.info(f'Data inserted successfully')
            except Exception as ex:
                lcparkLogs.error(f'EXCEPTION OCCURRED WHILE SYNCING SAP DATA WITH EMPLOYEE MASTER DATA')
                lcparkLogs.error(ex)
                lcparkLogs.error(traceback.format_exc())

                context = {'ex': str(ex)}
                mail_content = render_html_message_simple('SYNCING_ERROR_MAIL', context)
                mail_sent = PublishMail(
                    mail_subject="SAP SYNCING FAILED",
                    mail_content=mail_content,
                    to="anshu.agarwal@amns.in",
                    cc="",
                    sender_email="exit@amns.in",
                    mailserver="mail.myamns.in",
                    auth=False,
                    rcpt_options=['NOTIFY=DELAY,FAILURE']
                )

            # Inserting all data into postgres
            # try:
            #     data_df.to_sql('TRANS_RESIGNATION_DATA', con=conn_postgres, index=False, if_exists='append')
            #     lcparkLogs.info(f'Data inserted successfully')r
            # except Exception as ex:
            #     lcparkLogs.error(f'Did not insert data --> Error --> {ex}')
        except Exception as ex:
            lcparkLogs.error(f'Did not insert data --> Error --> {ex}')

    def handle(self, *args, **options):
        """
        used as entry point for management command
        """
        self.insert_data()
