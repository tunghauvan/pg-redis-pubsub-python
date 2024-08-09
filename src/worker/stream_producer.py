import json
import logging
import time
import select
import psycopg2
import redis
from redlock import Redlock
import os
from event_schema import EventSchema
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# Assuming REDIS_HOST, REDIS_PORT, REDIS_DB, POSTGRES_LISTENNER, REDIS_STREAM are defined elsewhere
POSTGRES_DSN = os.environ.get(
    'POSTGRES_DSN',
    'postgres://postgres:postgres@localhost:5432/postgres'
)

POSTGRES_LISTENNER = os.environ.get(
    'POSTGRES_LISTENNER',
    'table_change'
)

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_DB = os.environ.get('REDIS_DB', 0)
REDIS_CHANNEL = os.environ.get('REDIS_CHANNEL', 'table_change')
REDIS_STREAM = os.environ.get('REDIS_STREAM', 'table_change_stream')
dlm = Redlock([{"host": REDIS_HOST, "port": REDIS_PORT, "db": REDIS_DB}])


def add_event_to_stream(redis_client, stream_name, event_id, event_data):
    # Acquire lock for the specific event_id
    # Lock for hour
    lock = dlm.lock(f"lock:{event_id}", 1000 * 60 * 60)
    if lock:
        try:
            redis_client.xadd(stream_name, {event_id: event_data})
            return True
        except:
            logging.error(f"Failed to add event {event_id} to stream")
            dlm.unlock(lock)
            return False
    else:
        logging.warning(f"Failed to acquire lock for event {event_id}")
        return False


def worker():
    try:
        conn = psycopg2.connect(
            dsn=POSTGRES_DSN
        )
        conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"LISTEN {POSTGRES_LISTENNER};")
        logging.info(
            f"Connected to PostgreSQL and listening to {POSTGRES_LISTENNER}")

        redis_client = redis.StrictRedis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB
        )
        logging.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

        logging.info(
            f"Waiting for notifications on channel '{POSTGRES_LISTENNER}'")
        while True:
            if select.select([conn], [], [], 5) == ([], [], []):
                logging.debug("Timeout")
            else:
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    event = EventSchema.from_json(json.loads(notify.payload))
                    logging.info(f"Received event {event.event_uuid}")
                    result = add_event_to_stream(
                        redis_client,
                        REDIS_STREAM,
                        event.event_uuid,
                        event.to_json()
                    )
                    if result:
                        logging.info(
                            f"Event {event.event_uuid} added to stream")
                    else:
                        logging.warning(
                            f"Failed to add event {event.event_uuid} to stream")

    except psycopg2.OperationalError as e:
        logging.error(f"PostgreSQL connection failed: {e}")
        time.sleep(5)  # Wait for 5 seconds before retrying
    except redis.ConnectionError as e:
        logging.error(f"Redis connection failed: {e}")
        time.sleep(5)  # Wait for 5 seconds before retrying
