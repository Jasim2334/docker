# Install required packages
pip install requests psycopg2

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
    password="Jasim@123",
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

# Write to PostgreSQL
cursor = conn.cursor()
for record in flattened_data:
    cursor.execute("INSERT INTO your_table_name VALUES (%s)" % ','.join(['%s'] * len(record)), list(record.values()))
conn.commit()
cursor.close()
conn.close()

