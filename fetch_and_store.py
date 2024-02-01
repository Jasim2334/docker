import requests
from bs4 import BeautifulSoup
import psycopg2
from flatten_json import flatten
from datetime import datetime
import logging

# Configure logging to write messages to a file
logging.basicConfig(filename='script_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URL of the page containing JSON API links
base_url = "https://www.circl.lu/doc/misp/feed-osint/"

# Function to flatten JSON (modified to handle nested structures)
def flatten_json(data, parent_key='', sep='_'):
    flat_data = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            flat_data.update(flatten_json(value, new_key, sep=sep))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                flat_data.update(flatten_json(item, f"{new_key}{sep}{i}", sep=sep))
        else:
            flat_data[new_key] = value
    return flat_data

try:
    # Fetch HTML content of the page
    response = requests.get(base_url)
    response.raise_for_status()  # Raises HTTPError for bad responses
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract JSON API URLs
    api_urls = [f"{base_url}{a['href']}" for a in soup.find_all('a', href=True) if a['href'].endswith('.json')]

    # Take only the first API URL
    if api_urls:
        json_api_url = api_urls[0]
        
        try:
            # PostgreSQL Connection
            conn = psycopg2.connect(
                database="de_haze",
                user="postgres",
                password="jasim@123",
                host="192.168.44.131",
                port="5432"
            )
            
            try:
                # Fetch data from API
                response = requests.get(json_api_url)
                response.raise_for_status()

                # Check if the response content is not empty
                if response.text:
                    try:
                        # Attempt to parse the JSON content
                        data = response.json()

                        # Check if the "Event" key is present in the data
                        if "Event" in data:
                            # If the API response is a single event
                            event_data = data["Event"]

                            # Flatten Event and Orgc sections
                            flattened_event = flatten_json(event_data)

                            # Limit the number of fields to include in the table (adjust as needed)
                            max_fields = 50
                            selected_fields = list(flattened_event.keys())[:max_fields]

                            # Generate the CREATE TABLE query dynamically with a JSONB column for attributes
                            create_table_query = f"""
                                CREATE TABLE IF NOT EXISTS docker_all_json_api (
                                    id SERIAL PRIMARY KEY,
                                    {', '.join(f'{field} VARCHAR(255)' for field in selected_fields)}
                                );
                            """

                            # Create the table and insert data in the same transaction
                            with conn.cursor() as cursor:
                                cursor.execute(create_table_query)

                                # Convert timestamps to a valid datetime format if they're present
                                for timestamp_field in ['Event_timestamp']:
                                    if timestamp_field in flattened_event:
                                        flattened_event[timestamp_field] = datetime.utcfromtimestamp(
                                            int(flattened_event[timestamp_field])
                                        ).strftime('%Y-%m-%d %H:%M:%S')

                                # Insert data into docker_all_json_api table
                                insert_query = f"""
                                    INSERT INTO docker_all_json_api ({', '.join(selected_fields)})
                                    VALUES ({', '.join(['%s']*len(selected_fields))});
                                """
                                cursor.execute(insert_query, [flattened_event[field] for field in selected_fields])

                            conn.commit()
                            logging.info("Data insertion into the database successful")
                        else:
                            logging.error("The API response structure is not as expected.")
                    except ValueError as e:
                        logging.error(f"Error parsing JSON: {e}")
                else:
                    logging.warning("Empty response from the API.")
            except requests.exceptions.RequestException as e:
                logging.error(f"Error in request to API: {e}")
        except psycopg2.Error as e:
            logging.error(f"Error connecting to the database: {e}")
        finally:
            if conn:
                conn.close()
    else:
        logging.warning("No API URLs found.")
except requests.exceptions.RequestException as e:
    logging.error(f"Error in initial request: {e}")
except Exception as e:
    logging.exception(f"An unexpected error occurred: {e}")

