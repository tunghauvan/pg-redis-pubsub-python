# PG Redis PubSub Python

This repository contains a Python application that listens to Redis Pub/Sub messages and processes them by fetching related data from a PostgreSQL database.

## Prerequisites

- Docker
- Docker Compose

## Setup

1. Clone the repository:
```sh
git clone https://github.com/tunghauvan/pg-redis-pubsub-python.git
cd pg-redis-pubsub-python
```

2. Build and start the Docker containers:
```sh
docker-compose up --build -d
```

## Test message 
```sh
docker-compose exec -it postgres psql -U postgres -c "INSERT INTO message (content) VALUES ('Hello, I need you to confirm');" 
```

## View event
```sh
docker compose logs consumer-agent -f
```
