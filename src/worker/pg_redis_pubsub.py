import json
import psycopg2
import select
import redis
import time
import os
import logging

from eventter import EventSchema

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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


def publish_unique_event(r, channel, event_uuid, event_data):
    lock_key = f"lock:{event_uuid}"
    event_key = f"event:{event_uuid}"

    # Try to acquire the lock
    if r.setnx(lock_key, 'locked'):
        try:
            # Set an expiration for the lock to avoid deadlocks
            r.expire(lock_key, 10)  # 10 seconds expiration

            # Check if the event has already been processed
            if not r.hget('event_metadata', event_uuid):
                r.hset('event_metadata', event_uuid, 'processed')
                r.publish(channel, event_data)
                logging.info(f"Published event {event_uuid} to channel {channel}")
            else:
                logging.info(f"Event {event_uuid} has already been processed")
        finally:
            # Release the lock
            r.delete(lock_key)
    else:
        # If lock is not acquired, wait and retry
        time.sleep(0.1)
        publish_unique_event(r, channel, event_uuid, event_data)


def worker():
    while True:
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(
                dsn=POSTGRES_DSN
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            cur.execute(f"LISTEN {POSTGRES_LISTENNER};")
            logging.info(f"Connected to PostgreSQL and listening to {POSTGRES_LISTENNER}")

            # Connect to Redis
            redis_client = redis.StrictRedis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB
            )
            logging.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

            logging.info(f"Waiting for notifications on channel '{POSTGRES_LISTENNER}'")
            while True:
                if select.select([conn], [], [], 5) == ([], [], []):
                    logging.debug("Timeout")
                else:
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        event = EventSchema.from_json(json.loads(notify.payload))
                        logging.info(f"Received event {event.event_uuid}")
                        publish_unique_event(
                            redis_client,
                            REDIS_CHANNEL,
                            event.event_uuid,
                            event.to_json()
                        )
        except psycopg2.OperationalError as e:
            logging.error(f"PostgreSQL connection failed: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying
        except redis.ConnectionError as e:
            logging.error(f"Redis connection failed: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying