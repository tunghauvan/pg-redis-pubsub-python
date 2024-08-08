from eventter import EventSchema
import logging
import psycopg2
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# PostgreSQL connection details
POSTGRES_DSN = os.environ.get(
    'POSTGRES_DSN',
    'postgres://postgres:postgres@localhost:5432/postgres'
)

def main(event: EventSchema):
    event_id = event.id
    event_table = event.table
    logging.info(f"RECORD_ID: {event_id}, TABLE: {event_table}")

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(dsn=POSTGRES_DSN)
        cur = conn.cursor()

        # Fetch data based on event details
        query = f"SELECT * FROM {event_table} WHERE id = %s"
        cur.execute(query, (event_id,))
        result = cur.fetchone()

        if result:
            logging.info(f"Fetched data: {result}")
        else:
            logging.info(f"No data found for RECORD_ID: {event_id} in TABLE: {event_table}")

        # Close the cursor and connection
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        logging.error(f"Error fetching data from PostgreSQL: {e}")
