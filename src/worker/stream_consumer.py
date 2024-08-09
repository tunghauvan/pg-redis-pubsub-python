import json
import logging
import time
import redis
import os

from typing import Callable
from redlock import Redlock
from event_schema import EventSchema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# Assuming REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_STREAM are defined elsewhere
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_DB = os.environ.get('REDIS_DB', 0)
REDIS_STREAM = os.environ.get('REDIS_STREAM', 'table_change_stream')
GROUP_NAME = os.environ.get('REDIS_GROUP', 'consumer_group')
CONSUMER_NAME = os.environ.get('REDIS_CONSUMER', 'consumer_1')

# Initialize Redis client and Redlock
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
dlm = Redlock([{"host": REDIS_HOST, "port": REDIS_PORT, "db": REDIS_DB}])

# Create consumer group if it doesn't exist
try:
    redis_client.xgroup_create(REDIS_STREAM, GROUP_NAME, id='0', mkstream=True)
except redis.exceptions.ResponseError as e:
    if "BUSYGROUP Consumer Group name already exists" not in str(e):
        raise

# Define a default handler function


def default_handler(event: EventSchema):
    logging.info(f"Handled event: {event.id}")


def process_event(event_id, event_data, handler: Callable[[EventSchema], None] = default_handler):
    # Acquire lock for the specific event_id
    # Lock for 1 hour
    lock = dlm.lock(f"lock:{event_id}", 1000 * 60 * 60)
    if lock:
        try:
            event = EventSchema.from_json_str(event_data.decode('utf-8'))
            # Process the event (this is where your custom logic goes)
            handler(event)
        finally:
            # Release lock
            dlm.unlock(lock)
    else:
        logging.info(
            f"Could not acquire lock for event {event_id}, another consumer is processing")
        time.sleep(0.1)  # Wait before retrying


def worker(handler: Callable[[EventSchema], None] = default_handler, filters={}):
    logging.info(f"Starting consumer {CONSUMER_NAME} for group {GROUP_NAME}")
    while True:
        try:
            # Read events from the Redis Stream
            events = redis_client.xreadgroup(
                GROUP_NAME, CONSUMER_NAME,
                {REDIS_STREAM: '>'},
                count=10,
                block=5000
            )

            for stream, messages in events:
                for message_id, message_data in messages:
                    event_id = list(message_data.keys())[0]
                    event_data = message_data[event_id]
                    process_event(event_id, event_data, handler)
                    # Acknowledge the message
                    redis_client.xack(REDIS_STREAM, GROUP_NAME, message_id)
        except redis.ConnectionError as e:
            logging.error(f"Redis connection failed: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker()
