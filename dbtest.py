import psycopg2
from psycopg2.extras import execute_values
import os

# Assuming POSTGRES_DSN is defined in the environment variables
POSTGRES_DSN = os.environ.get(
    'POSTGRES_DSN',
    'postgres://postgres:postgres@localhost:5432/postgres'
)


def insert_messages(messages):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(dsn=POSTGRES_DSN)
        cur = conn.cursor()

        # Prepare the SQL query for bulk insert
        query = "INSERT INTO message (content) VALUES %s"

        # Use execute_values to perform the bulk insert
        execute_values(cur, query, messages)

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()

        print("Messages inserted successfully.")
    except psycopg2.Error as e:
        print(f"Error inserting messages: {e}")


def generate_random_message(number_of_message: int):
    messages = []
    for i in range(number_of_message):
        messages.append((f"Message {i}",))
    return messages


if __name__ == "__main__":
    messages = generate_random_message(100)
    insert_messages(messages)
