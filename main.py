from fastapi import FastAPI, HTTPException
import duckdb
from config import Config
import logging
from app.oracle_to_duckdb import OracleToDuckDBProcessor

app = FastAPI()

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OracleToDuckDBProcessor
processor = OracleToDuckDBProcessor()

def query_duckdb(sql_query):
    try:
        with duckdb.connect(Config.DUCKDB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            result = cursor.fetchall()
            return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        logging.error(f"DuckDB query error: {e}")
        raise

@app.get("/columns/")
async def get_columns():
    try:
        columns = query_duckdb("PRAGMA table_info('mapview_crashes')")
        return {"columns": [col['name'] for col in columns]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/record_count/")
async def get_record_count():
    try:
        record_count = query_duckdb("SELECT COUNT(*) AS count FROM mapview_crashes")[0]['count']
        return {"record_count": record_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/records/")
async def get_records(page: int = 1, size: int = 10):
    try:
        offset = (page - 1) * size
        records = query_duckdb(f"SELECT * FROM mapview_crashes LIMIT {size} OFFSET {offset}")
        return {"data": records}
    except Exception as e:
        logging.error(f"Error fetching records: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/records/{column}/{value}")
async def get_records_by_column(column: str, value: str):
    try:
        records = query_duckdb(f"SELECT * FROM mapview_crashes WHERE {column} = '{value}'")
        return {"data": records}
    except Exception as e:
        logging.error(f"Error fetching records by column: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/record/{index}")
async def get_record(index: int):
    try:
        records = query_duckdb(f"SELECT * FROM mapview_crashes LIMIT 1 OFFSET {index}")
        if not records:
            raise HTTPException(status_code=404, detail=f"Record with index {index} not found")
        return {"data": records[0]}
    except Exception as e:
        logging.error(f"Error fetching record: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/update_database/")
async def update_database():
    try:
        processor.process_data()
        return {"message": "Database updated successfully"}
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        raise HTTPException(status_code=500, detail="Error updating database")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
