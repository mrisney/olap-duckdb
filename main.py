import duckdb
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
        raise HTTPException(status_code=500, detail=f"DuckDB query error: {e}")

# Mount the static directory to serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/counties")
async def get_counties():
    try:
        query = "SELECT DISTINCT vchcounty FROM mapview_crashes ORDER BY vchcounty ASC"
        result = query_duckdb(query)
        counties = [row['vchcounty'] for row in result]
        return counties
    except Exception as e:
        logger.error(f"Error fetching counties: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/daily_crashes/{county}")
async def get_daily_crashes(county: str, year: int):
    try:
        query = """
            SELECT epoch(datcrashdate) AS timestamp, COUNT(*) AS crash_count
            FROM mapview_crashes
            WHERE vchcounty = ? AND EXTRACT(YEAR FROM datcrashdate) = ?
            GROUP BY datcrashdate
            ORDER BY datcrashdate
        """
        crashes = query_duckdb(query, (county, year))
        if not crashes:
            return {}

        return {int(crash['timestamp']): crash['crash_count'] for crash in crashes}
    except Exception as e:
        logger.error(f"Error fetching daily crashes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/geojson/{county}")
async def get_geojson(county: str, year: int = None, date: str = None):
    try:
        if year:
            query = """
                SELECT longitude, latitude, vchcrashcasenumber, datcrashdate, tintcrashseverity,
                       ST_Within(
                           ST_GeomFromText('POINT(' || longitude || ' ' || latitude || ')'),
                           ST_GeomFromText('POLYGON(( -111.0569 45.0037, -104.0521 45.0037, -104.0521 40.9945, -111.0569 40.9945, -111.0569 45.0037 ))')
                       ) AS within_wyoming
                FROM mapview_crashes
                WHERE vchcounty = ? AND EXTRACT(YEAR FROM datcrashdate) = ?
            """
            params = (county, year)
        elif date:
            query = """
                SELECT longitude, latitude, vchcrashcasenumber, datcrashdate, tintcrashseverity,
                       ST_Within(
                           ST_GeomFromText('POINT(' || longitude || ' ' || latitude || ')'),
                           ST_GeomFromText('POLYGON(( -111.0569 45.0037, -104.0521 45.0037, -104.0521 40.9945, -111.0569 40.9945, -111.0569 45.0037 ))')
                       ) AS within_wyoming
                FROM mapview_crashes
                WHERE vchcounty = ? AND datcrashdate = ?
            """
            params = (county, date)
        else:
            raise HTTPException(status_code=400, detail="Year or date must be provided.")

        crashes = query_duckdb(query, params)
        if not crashes:
            logger.info(f"No records found for county: {county}")
            return {"type": "FeatureCollection", "features": []}

        features = []
        for crash in crashes:
            if crash['within_wyoming']:
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [crash['longitude'], crash['latitude']]
                    },
                    "properties": {
                        "vchcrashcasenumber": crash['vchcrashcasenumber'],
                        "datcrashdate": crash['datcrashdate'].isoformat(),
                        "tintcrashseverity": crash['tintcrashseverity']
                    }
                }
                features.append(feature)

        geojson = {"type": "FeatureCollection", "features": features}
        logger.info(f"Generated GeoJSON for county: {county}, features: {len(features)}")
        return geojson
    except Exception as e:
        logger.error(f"Error fetching GeoJSON data: {e}")
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
