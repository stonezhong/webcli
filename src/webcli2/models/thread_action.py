from ._common import CoreModelBase
from .action import Action
from webcli2.db_models import DBThreadAction

class ThreadAction(CoreModelBase):
    id: int
    thread_id: int
    action: Action
    display_order: int
    show_question: bool
    show_answer: bool

    @classmethod
    def create(self, db_thread_action:DBThreadAction) -> "ThreadAction":
        return ThreadAction(
            id = db_thread_action.id,
            thread_id = db_thread_action.thread_id,
            action_id = db_thread_action.action_id,
            action = Action.create(db_thread_action.action),
            display_order = db_thread_action.display_order,
            show_question = db_thread_action.show_question,
            show_answer = db_thread_action.show_answer
        )

