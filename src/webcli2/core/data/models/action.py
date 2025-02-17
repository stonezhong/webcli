from __future__ import annotations

from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel
from webcli2.core.data.db_models import DBAction
from .action_response_chunk import ActionResponseChunk

#############################################################################
# Represent an action
# ---------------------------------------------------------------------------
# It wraps the DB layer action
#############################################################################
class Action(BaseModel):
    id: int
    handler_name: str
    is_completed: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    request: dict
    title: str
    raw_text: str
    response_chunks: List[ActionResponseChunk] = []


    @classmethod
    def from_db(cls, db_action:DBAction) -> "Action":
        return Action(
            id = db_action.id,
            handler_name = db_action.handler_name,
            is_completed = db_action.is_completed,
            created_at = db_action.created_at,
            completed_at = db_action.completed_at,
            request = db_action.request,
            title = db_action.title,
            raw_text = db_action.raw_text,
            response_chunks = []
        )
