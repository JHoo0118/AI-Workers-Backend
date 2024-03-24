from collections import deque
import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.model.base_model import BaseSchema
from app.utils.datetime_utils import getNow


class EventModel(BaseSchema):
    task_id: str
    task_type: str
    result: Optional[str] = None
    message: Optional[str] = None
    completed: bool = False
    error: bool = False
    created_at: datetime.datetime = getNow()
    completed_at: Optional[datetime.datetime] = None
    request_body: Optional[Any] = None


class SSEEvent:
    EVENTS: dict[str, EventModel] = dict()

    @staticmethod
    def add_event(event: EventModel):
        SSEEvent.EVENTS[event.task_id] = event

    @staticmethod
    def get_event(task_id: str):
        if len(SSEEvent.EVENTS) > 0 and SSEEvent.EVENTS.get(task_id) is not None:
            return SSEEvent.EVENTS[task_id]
        return None

    @staticmethod
    def count():
        return len(SSEEvent.EVENTS)


class SSEEmitInputs(EventModel):
    pass


class SSEEmitOutputs(EventModel):
    pass
