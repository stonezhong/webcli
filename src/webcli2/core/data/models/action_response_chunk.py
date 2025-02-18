from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from webcli2.core.data.db_models import DBActionResponseChunk

#############################################################################
# Represent an action
# ---------------------------------------------------------------------------
# It wraps the DB layer action
#############################################################################
class ActionResponseChunk(BaseModel):
    id: int
    action_id: int
    order: int
    mime: str
    text_content: Optional[str] = None
    binary_content: Optional[bytes] = Field(exclude=True, default=None)

    @classmethod
    def from_db(cls, db_action_response_chunk:DBActionResponseChunk) -> "ActionResponseChunk":
        return ActionResponseChunk(
            id = db_action_response_chunk.id,
            action_id = db_action_response_chunk.action_id,
            order = db_action_response_chunk.order,
            mime = db_action_response_chunk.mime,
            text_content = db_action_response_chunk.text_content,
            binary_content = db_action_response_chunk.binary_content
        )
