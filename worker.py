import yaml
import importlib
import fire

# Load the YAML configuration
with open('worker.yaml', 'r') as file:
    config = yaml.safe_load(file)


def load_handler(module_name, handler_name):
    module = importlib.import_module(module_name)
    return getattr(module, handler_name)


def load_worker(module_name, worker_name):
    module = importlib.import_module(module_name)
    return getattr(module, worker_name)


class Worker():
    pass


# Dynamically create worker methods based on the configuration
for worker in config['workers']:
    name = worker['name']
    worker_module = worker.get('worker_module', None)
    worker_name = worker.get('worker_name', None)

    if not worker_module:
        print(f"Worker {worker_name} has no worker_module defined")
        continue

    handler_module = worker.get('handler_module', None)
    handler_name = worker.get('handler_name', None)

    if handler_module and handler_name:
        filters = worker.get('filters', {})

        def worker_method(self, worker_module=worker_module, worker_name=worker_name, handler_module=handler_module, handler_name=handler_name, filters=filters):
            worker = load_worker(worker_module, worker_name)
            handler = load_handler(handler_module, handler_name)
            worker(handler=handler, filters=filters)

        setattr(Worker, name, worker_method)

    else:
        def worker_method(self, worker_module=worker_module, worker_name=worker_name):
            worker = load_worker(worker_module, worker_name)
            worker()

        setattr(Worker, name, worker_method)

if __name__ == '__main__':
    try:
        fire.Fire(Worker)
    except KeyboardInterrupt:
        print("Terminated by user")
