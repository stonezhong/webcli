from typing import Optional, List
from datetime import datetime

from ._common import CoreModelBase
from webcli2.db_models import DBThread, DBThreadAction
from .thread_action import ThreadAction

class Thread(CoreModelBase):
    id: int
    user_id: int
    created_at: datetime
    title: str
    description: str

    thread_actions: Optional[List[ThreadAction]]

    @classmethod
    def create(self, db_thread:DBThread, db_thread_actions:Optional[List[DBThreadAction]]=None) -> "Thread":
        return Thread(
            id = db_thread.id,
            user_id = db_thread.user_id,
            created_at = db_thread.created_at,
            title = db_thread.title,
            description = db_thread.description,
            thread_actions = None if db_thread_actions is None else [
                ThreadAction.create(db_thread_action) for db_thread_action in db_thread_actions
            ]
        )


