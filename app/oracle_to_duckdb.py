import cx_Oracle
import pandas as pd
import duckdb
from sqlalchemy import create_engine
from config import Config
import logging

class OracleToDuckDBProcessor:
    def __init__(self):
        self.oracle_engine = create_engine(Config.ORACLE_DSN)
        self.duckdb_conn = duckdb.connect(Config.DUCKDB_FILE)
        self.parquet_file = Config.PARQUET_FILE_PATH
        logging.info("Initialized Oracle to DuckDB Processor")

    def fetch_table_structure(self, synonym_name, owner):
        query = f"""
        SELECT DISTINCT c.column_name AS column_name, c.data_type AS data_type
        FROM all_synonyms s
        JOIN all_tab_columns c ON s.table_name = c.table_name
        WHERE s.synonym_name = '{synonym_name}'
        AND s.owner = '{owner}'
        """
        logging.info(f"Fetching table structure for synonym: {synonym_name}")
        df_structure = pd.read_sql(query, con=self.oracle_engine)
        logging.info(f"Table structure fetched: {df_structure}")
        return df_structure

    def map_types(self, df, df_structure):
        datatype_mapping = {
            "NUMBER": "float64",
            "VARCHAR2": "object",
            "DATE": "datetime64[ns]",
            "CHAR": "object",
            "TIMESTAMP": "datetime64[ns]",
            "TIME": "datetime64[ns]"
        }

        logging.info(f"Columns in df_structure: {df_structure.columns.tolist()}")
        logging.info(f"Columns in fetched data: {df.columns.tolist()}")

        for _, row in df_structure.iterrows():
            col = row['column_name'].strip().lower()
            dtype = row['data_type'].strip().upper()
            if col in df.columns:
                if dtype in datatype_mapping:
                    mapped_type = datatype_mapping[dtype]
                    logging.info(f"Mapping column {col} with type {dtype.lower()} to {mapped_type}")
                    df[col] = df[col].astype(mapped_type)
                else:
                    logging.warning(f"Skipping column {col} with type {dtype} (not mapped)")
            else:
                logging.warning(f"Column {col} not found in data")

        return df

    def process_data(self):
        try:
            synonym_name = 'MAPVIEW_CRASHES'
            owner = 'OS_ADMIN'
            df_structure = self.fetch_table_structure(synonym_name, owner)

            query = f"""
            SELECT
                t.*,
                SDO_UTIL.TO_GEOJSON(t.geometry) AS geometry_geojson
            FROM {synonym_name} t
            """
            logging.info(f"Executing query: {query}")
            df = pd.read_sql(query, con=self.oracle_engine)
            logging.info("Data fetched from Oracle")

            df = self.map_types(df, df_structure)
            df.drop(columns=['geometry'], inplace=True)
            df.rename(columns={'geometry_geojson': 'geometry'}, inplace=True)

            self.update_duckdb(df, synonym_name.lower())
        except Exception as e:
            logging.error(f"Error in processing data: {e}")
            raise e

    def update_duckdb(self, df, table_name):
        try:
            logging.info(f"Updating DuckDB table {table_name} with data shape: {df.shape}")
            df.to_parquet(self.parquet_file)
            self.duckdb_conn.execute(f'CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_parquet("{self.parquet_file}") LIMIT 0')
            self.duckdb_conn.execute(f'INSERT INTO {table_name} SELECT * FROM read_parquet("{self.parquet_file}")')
        except Exception as e:
            logging.error(f"Error updating DuckDB with Oracle data and metadata: {e}")
            raise e

# Ensure logging is configured
logging.basicConfig(level=logging.INFO)

# If running as the main module, instantiate and run the processor
if __name__ == "__main__":
    processor = OracleToDuckDBProcessor()
    processor.process_data()
