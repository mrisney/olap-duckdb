import duckdb
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a DuckDB connection
con = duckdb.connect(database=':memory:')

# Enable the spatial extension
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

# Create the mapview_crashes table and insert some example data
con.execute("""
CREATE TABLE mapview_crashes (
    vchcounty VARCHAR,
    datcrashdate TIMESTAMP,
    longitude DOUBLE,
    latitude DOUBLE
);
""")

# Example data including a point in Albany county and other points
example_data = [
    ('ALBANY', '2024-01-01 00:00:00', -106.3131, 42.8501),  # Casper, WY
    ('ALBANY', '2024-02-01 00:00:00', -105.5000, 42.0000),  # Albany county
    ('ALBANY', '2024-03-01 00:00:00', -104.0000, 41.0000),  # Outside Wyoming
    ('NATRONA', '2024-01-01 00:00:00', -106.3131, 42.8501)  # Casper, WY
]

# Insert example data
con.executemany("INSERT INTO mapview_crashes VALUES (?, ?, ?, ?)", example_data)

# Define the query to test if points are within the Wyoming bounding box
wyoming_bbox = "POLYGON((\
    -111.0569 45.0037,\
    -104.0521 45.0037,\
    -104.0521 40.9945,\
    -111.0569 40.9945,\
    -111.0569 45.0037))"

query = f"""
SELECT
    longitude, latitude, ST_Within(
        ST_GeomFromText('POINT(' || longitude || ' ' || latitude || ')'),
        ST_GeomFromText('{wyoming_bbox}')
    ) AS within_wyoming
FROM mapview_crashes
WHERE vchcounty = ? AND EXTRACT(YEAR FROM datcrashdate) = ?
"""

params = ['ALBANY', 2024]
logger.info(f"Executing query: {query} with params: {params}")

try:
    result = con.execute(query, params).fetchall()
    for row in result:
        logger.info(f"Record: {row}")
except Exception as e:
    logger.error(f"Error executing query: {e}")

# Clean up
con.close()
