import os
import logging

class Config:
    ORACLE_USER = 'os_admin'
    ORACLE_PASSWORD = 'os_admin_4847'
    ORACLE_DSN = 'oracle+oracledb://os_admin:os_admin_4847@dev.oracle19.itis-db.com:1521/?service_name=ORCL'
    DUCKDB_FILE = '/Users/marcrisney/Projects/itis/olap-duckdb/data/mapview_crashes.duckdb'
    PARQUET_FILE = '/Users/marcrisney/Projects/itis/olap-duckdb/data/mapview_crashes.parquet'
    PARQUET_FILE_PATH = os.getenv('PARQUET_FILE_PATH', PARQUET_FILE)  # Ensuring PARQUET_FILE_PATH is set correctly
    
    @staticmethod
    def setup_logging():
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

Config.setup_logging()
