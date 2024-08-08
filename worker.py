import yaml
import importlib
import fire

from src.worker import pg_redis_consumer
from src.worker import pg_redis_pubsub

# Load the YAML configuration
with open('worker.yaml', 'r') as file:
    config = yaml.safe_load(file)


def load_handler(module_name, handler_name):
    module = importlib.import_module(module_name)
    return getattr(module, handler_name)


class Worker():
    pass


# Dynamically create worker methods based on the configuration
for worker in config['workers']:
    worker_name = worker['name']
    if 'handler_module' in worker and 'handler_name' in worker:
        handler_module = worker['handler_module']
        handler_name = worker['handler_name']
        filters = worker.get('filters', {})

        def worker_method(self, handler_module=handler_module, handler_name=handler_name, filters=filters):
            handler = load_handler(handler_module, handler_name)
            pg_redis_consumer.worker(handler=handler, filters=filters)

        setattr(Worker, worker_name, worker_method)
    else:
        def worker_method(self):
            if worker_name == 'consumer':
                pg_redis_consumer.worker()
            elif worker_name == 'producer':
                pg_redis_pubsub.worker()

        setattr(Worker, worker_name, worker_method)

if __name__ == '__main__':
    try:
        fire.Fire(Worker)
    except KeyboardInterrupt:
        print("Terminated by user")
