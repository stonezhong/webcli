from __future__ import annotations

from ._common import CoreModelBase
from .action import Action
from webcli2.core.data.db_models import DBThreadAction

class ThreadAction(CoreModelBase):
    id: int
    thread_id: int
    action: Action
    display_order: int
    show_question: bool
    show_answer: bool

