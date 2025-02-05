from typing import Any, Optional
from datetime import datetime

from ._common import CoreModelBase
from webcli2.db_models import DBAction, DBActionHandlerConfiguration, DBUser

#############################################################################
# Represent an action
# ---------------------------------------------------------------------------
# It wraps the DB layer action
#############################################################################
class Action(CoreModelBase):
    id: int
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request: dict
    response: Optional[dict]
    progress: Optional[dict]

    @classmethod
    def create(self, db_async_action:DBAction) -> "Action":
        return Action(
            id = db_async_action.id,
            is_completed = db_async_action.is_completed,
            created_at = db_async_action.created_at,
            updated_at = db_async_action.updated_at,
            completed_at = db_async_action.completed_at,
            request = db_async_action.request,
            response = db_async_action.response,
            progress = db_async_action.progress
        )


class ActionHandlerConfiguration(CoreModelBase):
    id: int
    action_handler_name: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    configuration: Optional[dict]

    @classmethod
    def create(self, db_ahc:DBActionHandlerConfiguration) -> "ActionHandlerConfiguration":
        return ActionHandlerConfiguration(
            id = db_ahc.id,
            action_handler_name = db_ahc.action_handler_name,
            user_id = db_ahc.user_id,
            created_at = db_ahc.created_at,
            updated_at = db_ahc.updated_at,
            configuration = db_ahc.configuration
        )

class User(CoreModelBase):
    id: int
    is_active: bool
    email: str
    password_version: int
    password_hash: str

    @classmethod
    def create(self, db_user:DBUser) -> "User":
        return User(
            id = db_user.id,
            is_active = db_user.is_active,
            email = db_user.email,
            password_version = db_user.password_version,
            password_hash = db_user.password_hash
        )

class JWTTokenPayload(CoreModelBase):
    email: str
    password_version: int
    sub: str
    uuid: str
