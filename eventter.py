from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class EventSchema:
    event_uuid: str
    event_created_at: datetime
    operation: str
    table: str
    id: int

    @staticmethod
    def from_json(json_data: dict):
        return EventSchema(
            event_uuid=json_data["event_uuid"],
            event_created_at=datetime.fromisoformat(
                json_data["event_created_at"]),
            operation=json_data["operation"],
            table=json_data["table"],
            id=json_data["id"]
        )
    
    def from_json_str(json_str: str):
        return EventSchema.from_json(json.loads(json_str))

    def to_json(self):
        return json.dumps(self, default=lambda o: o.isoformat() if isinstance(o, datetime) else o.__dict__)
    
    
# main handler
if __name__ == "__main__":
    event = EventSchema(
        event_uuid="123e4567-e89b-12d3-a456-426614174000",
        event_created_at=datetime.now(),
        operation="insert",
        table="users",
        id=1
    )
    
    print(event.to_json())