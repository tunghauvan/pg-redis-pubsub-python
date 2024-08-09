import os
import redis
import time
import logging
from event_schema import EventSchema

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
REDIS_DB = os.environ.get('REDIS_DB', 0)
REDIS_CHANNEL = os.environ.get('REDIS_CHANNEL', 'table_change')


def eventFilter(event, filters):
    logging.info(f"Filtering event: {event}")
    # loop dict
    for key, value in filters.items():
        if getattr(event, key) != value:
            logging.info(f"Event {event} does not match filter {key}={value}")
            return None
    return event


def worker(handler, filters):
    try:
        # Connect to Redis
        redis_client = redis.StrictRedis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB
        )

        # Subscribe to the channel
        pubsub = redis_client.pubsub()
        pubsub.subscribe(REDIS_CHANNEL)

        logging.info(f"Subscribed to '{REDIS_CHANNEL}'")

        # Consume messages
        for message in pubsub.listen():
            if message['type'] == 'message':
                event_data = message.get('data').decode('utf-8')
                # load event
                event = EventSchema.from_json_str(
                    event_data
                )
                # filter
                event = eventFilter(event, filters)

                if event is None:
                    continue

                handler(event)
    except redis.ConnectionError as e:
        logging.error(f"Redis connection failed: {e}")
        time.sleep(5)  # Wait for 5 seconds before retrying