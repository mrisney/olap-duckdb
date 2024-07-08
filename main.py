from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import duckdb
import json
import logging
from config import Config
from app.oracle_to_duckdb import OracleToDuckDBProcessor

app = FastAPI()

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OracleToDuckDBProcessor
processor = OracleToDuckDBProcessor()

def query_duckdb(sql_query, params=None):
    try:
        with duckdb.connect(Config.DUCKDB_FILE) as conn:
            conn.execute("INSTALL spatial;")
            conn.execute("LOAD spatial;")
            cursor = conn.cursor()
            if params:
                cursor.execute(sql_query, params)
            else:
                cursor.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            result = cursor.fetchall()
            return [dict(zip(columns, row)) for row in result]
    except Exception as e:
        logging.error(f"DuckDB query error: {e}")
        raise

# Mount the static directory to serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
async def get_records_by_column(column: str, value: str, page: int = 1, size: int = 10):
    try:
        offset = (page - 1) * size
        records = query_duckdb(f"SELECT * FROM mapview_crashes WHERE {column} = ? LIMIT {size} OFFSET {offset}", [value])
        return {"data": records}
    except Exception as e:
        logging.error(f"Error fetching records by column: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/earliest_date/")
async def get_earliest_date():
    try:
        result = query_duckdb("SELECT MIN(datcrashdate) AS earliest_date FROM mapview_crashes")
        earliest_date = result[0]['earliest_date']
        return {"earliest_date": earliest_date}
    except Exception as e:
        logging.error(f"Error fetching earliest date: {e}")
        raise HTTPException(status_code=500, detail="Error fetching earliest date")

@app.get("/counties")
async def get_counties():
    try:
        counties = query_duckdb("SELECT DISTINCT vchcounty FROM mapview_crashes ORDER BY vchcounty")
        return [county['vchcounty'] for county in counties]
    except Exception as e:
        logging.error(f"Error fetching counties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/daily_crashes/{county}")
async def get_daily_crashes(county: str):
    try:
        query = """
            SELECT 
                EXTRACT(EPOCH FROM datcrashdate) AS timestamp, 
                COUNT(*) AS crash_count
            FROM mapview_crashes
            WHERE vchcounty = ?
            GROUP BY datcrashdate
            ORDER BY datcrashdate
        """
        crashes = query_duckdb(query, [county])
        return {int(crash['timestamp']): crash['crash_count'] for crash in crashes}
    except Exception as e:
        logging.error(f"Error fetching daily crashes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/geojson/{county}")
async def get_geojson(county: str):
    try:
        query = """
            SELECT
                longitude, latitude, vchcounty, datcrashdate
            FROM mapview_crashes
            WHERE vchcounty = ?
        """
        result = query_duckdb(query, [county])
        
        if not result:
            logger.info(f"No records found for county: {county}")
            raise HTTPException(status_code=404, detail="No records found for the specified county")
        
        logger.info(f"Fetched {len(result)} records for county: {county}")
        for row in result:
            logger.info(f"Record: {row}")

        features = []
        for row in result:
            if row['longitude'] is not None and row['latitude'] is not None:
                geojson = {
                    "type": "Point",
                    "coordinates": [row['longitude'], row['latitude']]
                }
                features.append({
                    "type": "Feature",
                    "geometry": geojson,
                    "properties": {}  # Add any additional properties if needed
                })
        
        logger.info(f"Generated GeoJSON for county: {county}, features: {len(features)}")
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
    except Exception as e:
        logging.error(f"Error fetching GeoJSON data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/update_database/")
async def update_database():
    try:
        processor.process_data()
        return {"message": "Database updated successfully"}
    except Exception as e:
        logger.error(f"Error updating database: {e}")
        raise HTTPException(status_code=500, detail="Error updating database")

@app.get("/")
async def root():
    return FileResponse('static/index.html')

@app.get("/heatmap.html")
async def heatmap():
    return FileResponse('static/heatmap.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
