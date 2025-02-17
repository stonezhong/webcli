from __future__ import annotations

from typing import List
from datetime import datetime

from pydantic import BaseModel
from webcli2.core.data.db_models import DBThread
from webcli2.core.data.models import User, ThreadAction

class Thread(BaseModel):
    id: int
    user: User    
    created_at: datetime
    title: str
    description: str
    thread_actions: List[ThreadAction] = []

    @classmethod
    def from_db(cls, db_thread:DBThread) -> "ThreadSummary":
        return Thread(
            id = db_thread.id,
            user = User.from_db(db_thread.user),
            created_at = db_thread.created_at,
            title = db_thread.title,
            description = db_thread.description,
            thread_actions = []
        )

class ThreadSummary(BaseModel):
    id: int
    user: User
    created_at: datetime
    title: str
    description: str

    @classmethod
    def from_db(cls, db_thread:DBThread) -> "ThreadSummary":
        return ThreadSummary(
            id = db_thread.id,
            user = User.from_db(db_thread.user),
            created_at = db_thread.created_at,
            title = db_thread.title,
            description = db_thread.description
        )
