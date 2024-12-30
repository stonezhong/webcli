from typing import Any, Optional
from datetime import datetime

from ._common import CoreModelBase
from webcli2.db_models import DBAsyncAction

class AsyncAction(CoreModelBase):
    id: int
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request: dict
    response: Optional[dict]
    progress: Optional[dict]

    @classmethod
    def create(self, db_async_action:DBAsyncAction) -> "DBAsyncAction":
        return AsyncAction(
            id = db_async_action.id,
            is_completed = db_async_action.is_completed,
            created_at = db_async_action.created_at,
            updated_at = db_async_action.updated_at,
            completed_at = db_async_action.completed_at,
            request = db_async_action.request,
            response = db_async_action.response,
            progress = db_async_action.progress
        )

