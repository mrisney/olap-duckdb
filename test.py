import duckdb
from config import Config

# Connect to DuckDB
con = duckdb.connect(database=Config.DUCKDB_FILE, read_only=False)
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")


# Load data into the table if needed
# Assuming you have data in a CSV file or other format
# con.execute("COPY mapview_crashes FROM 'path/to/your/data.csv' (FORMAT CSV, HEADER)")

# Verify the table structure
con.execute("DESCRIBE mapview_crashes").fetchall()
