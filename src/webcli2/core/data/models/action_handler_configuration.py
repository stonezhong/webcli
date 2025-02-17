from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel
from webcli2.core.data.db_models import DBActionHandlerConfiguration
from .user import User

class ActionHandlerConfiguration(BaseModel):
    id: int
    action_handler_name: str
    user:User
    created_at: datetime
    updated_at: Optional[datetime] = None
    configuration: Optional[dict] = None

    @classmethod
    def create(cls, db_ahc:DBActionHandlerConfiguration) -> "ActionHandlerConfiguration":
        return ActionHandlerConfiguration(
            id = db_ahc.id,
            action_handler_name = db_ahc.action_handler_name,
            user = User.from_db(db_ahc.user),
            created_at = db_ahc.created_at,
            updated_at = db_ahc.updated_at,
            configuration = db_ahc.configuration
        )

