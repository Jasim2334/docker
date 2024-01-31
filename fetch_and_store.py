# Install required packages
# Make sure to run this command outside of the script before executing the script
# pip install requests psycopg2 flatten_json

# Script fetch_and_store.py
import requests
import psycopg2
from flatten_json import flatten

# API URL
json_api_url = "https://www.circl.lu/doc/misp/feed-osint/0b988513-9535-42f0-9ebc-5d6aec2e1c79.json"

# PostgreSQL Connection
conn = psycopg2.connect(
    database="de_haze",
    user="postgres",
    password="jasim@123",
    host="localhost",
    port="5432"
)

# Function to flatten JSON
def flatten_json(data):
    return flatten(data, separator='_')

# Fetch data from API
response = requests.get(json_api_url)
data = response.json()

# Flatten fields
flattened_data = [flatten_json(record) for record in data[:100]]

# Identify unique fields from the flattened data
unique_fields = set(field for record in flattened_data for field in record.keys())

# Generate the CREATE TABLE query dynamically
create_table_query = f"CREATE TABLE IF NOT EXISTS docker_json (id SERIAL PRIMARY KEY, {', '.join(f'{field} VARCHAR(255)' for field in unique_fields)});"

# Create the table
cursor = conn.cursor()
cursor.execute(create_table_query)
conn.commit()

# Write to PostgreSQL
for record in flattened_data:
    insert_query = f"INSERT INTO docker_json ({', '.join(record.keys())}) VALUES ({', '.join(['%s']*len(record))})"
    cursor.execute(insert_query, list(record.values()))

conn.commit()
cursor.close()
conn.close()

