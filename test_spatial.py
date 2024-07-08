import duckdb
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the polygon representing Wyoming's boundaries
wyoming_bbox = "POLYGON((\
    -111.0569 45.0037,\
    -104.0521 45.0037,\
    -104.0521 40.9945,\
    -111.0569 40.9945,\
    -111.0569 45.0037))"

# Define a point in Casper, Wyoming
casper_point = "POINT(-106.3131 42.8501)"

# Initialize DuckDB connection
con = duckdb.connect(database=':memory:')

# Enable the spatial extension
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

# Create a table to store the point and the polygon
con.execute("""
CREATE TABLE spatial_test (
    id INTEGER,
    geom TEXT
);
""")

# Insert the polygon and the point into the table
con.execute("INSERT INTO spatial_test VALUES (1, ?)", [wyoming_bbox])
con.execute("INSERT INTO spatial_test VALUES (2, ?)", [casper_point])

# Use the ST_Within function to check if the point is within the polygon
query = """
SELECT 
    ST_Within(
        ST_GeomFromText((SELECT geom FROM spatial_test WHERE id = 2)),
        ST_GeomFromText((SELECT geom FROM spatial_test WHERE id = 1))
    ) AS within_wyoming
"""
result = con.execute(query).fetchall()

# Log the result
within_wyoming = result[0][0]
logger.info(f"Is the point in Casper, Wyoming within the Wyoming bounding box? {within_wyoming}")

# Clean up
con.close()
