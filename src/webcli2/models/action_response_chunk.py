from typing import Optional

from ._common import CoreModelBase
from webcli2.db_models import DBActionResponseChunk
from webcli2.webcli.output import MIMEType

#############################################################################
# Represent an action
# ---------------------------------------------------------------------------
# It wraps the DB layer action
#############################################################################
class ActionResponseChunk(CoreModelBase):
    id: int
    action_id: int
    order: int
    mime: MIMEType
    text_content: Optional[str]
    binary_content: Optional[bytes]

    @classmethod
    def create(self, db_action_response_chunk:DBActionResponseChunk) -> "ActionResponseChunk":
        return ActionResponseChunk(
            id = db_action_response_chunk.id,
            action_id = db_action_response_chunk.action_id,
            order = db_action_response_chunk.order,
            mime = db_action_response_chunk.mime,
            text_content = db_action_response_chunk.text_content,
            binary_content = db_action_response_chunk.binary_content
        )

