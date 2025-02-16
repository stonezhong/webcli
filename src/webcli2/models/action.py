from typing import Optional, List
from datetime import datetime

from ._common import CoreModelBase
from webcli2.db_models import DBAction, DBActionResponseChunk
from .action_response_chunk import ActionResponseChunk

#############################################################################
# Represent an action
# ---------------------------------------------------------------------------
# It wraps the DB layer action
#############################################################################
class Action(CoreModelBase):
    id: int
    handler_name: str
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request: dict
    title: str
    raw_text: str

    response_chunks: List[ActionResponseChunk]

    @classmethod
    def create(self, db_async_action:DBAction, db_response_chunks:List[DBActionResponseChunk]=[]) -> "Action":
        return Action(
            id = db_async_action.id,
            handler_name=db_async_action.handler_name,
            is_completed = db_async_action.is_completed,
            created_at = db_async_action.created_at,
            updated_at = db_async_action.updated_at,
            completed_at = db_async_action.completed_at,
            request = db_async_action.request,
            title = db_async_action.title,
            raw_text = db_async_action.raw_text,
            response_chunks = [
                ActionResponseChunk.create(db_response_chunk) for db_response_chunk in db_response_chunks
            ]
        )
