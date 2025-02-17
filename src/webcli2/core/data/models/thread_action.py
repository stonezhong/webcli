from __future__ import annotations

from pydantic import BaseModel
from .action import Action
from webcli2.core.data.db_models import DBThreadAction

class ThreadAction(BaseModel):
    id: int
    thread_id: int
    action: Action
    display_order: int
    show_question: bool
    show_answer: bool

