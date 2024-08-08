CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE message (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 1: Create the notify_change function
CREATE OR REPLACE FUNCTION notify_change()
RETURNS TRIGGER AS $$
DECLARE
    payload JSON;
    event_uuid UUID;
    event_created_at TIMESTAMP;
BEGIN
    -- Generate a UUID for the event
    event_uuid = uuid_generate_v4();

    -- Event time
    event_created_at = NOW();

    payload = json_build_object(
        'event_uuid', event_uuid,
        'event_created_at', event_created_at,
        'operation', TG_OP,
        'table', TG_TABLE_NAME,
        'id', NEW.id
    );
    PERFORM pg_notify('table_change', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 2: Create the trigger
CREATE TRIGGER trigger_notify_change
AFTER INSERT OR UPDATE OR DELETE ON message
FOR EACH ROW EXECUTE FUNCTION notify_change();