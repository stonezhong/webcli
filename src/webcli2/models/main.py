from typing import Any, Optional, List
from datetime import datetime

from ._common import CoreModelBase
from webcli2.db_models import DBAction, DBActionHandlerConfiguration, DBUser, \
    DBThread, DBThreadAction

#############################################################################
# Represent an action
# ---------------------------------------------------------------------------
# It wraps the DB layer action
#############################################################################
class Action(CoreModelBase):
    id: int
    handler_name: str
    is_completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    request: dict
    title: str
    raw_text: str
    response: Optional[dict]
    progress: Optional[dict]

    @classmethod
    def create(self, db_async_action:DBAction) -> "Action":
        return Action(
            id = db_async_action.id,
            handler_name=db_async_action.handler_name,
            is_completed = db_async_action.is_completed,
            created_at = db_async_action.created_at,
            updated_at = db_async_action.updated_at,
            completed_at = db_async_action.completed_at,
            request = db_async_action.request,
            title = db_async_action.title,
            raw_text = db_async_action.raw_text,
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

class Thread(CoreModelBase):
    id: int
    user_id: int
    created_at: datetime
    title: str

    thread_actions: Optional[List["ThreadAction"]]

    @classmethod
    def create(self, db_thread:DBThread, db_thread_actions:Optional[List["DBThreadAction"]]=None) -> "Thread":
        return Thread(
            id = db_thread.id,
            user_id = db_thread.user_id,
            created_at = db_thread.created_at,
            title = db_thread.title,
            thread_actions = None if db_thread_actions is None else [
                ThreadAction.create(db_thread_action) for db_thread_action in db_thread_actions
            ]
        )

class CreateThreadRequest(CoreModelBase):
    title: str

class CreateActionRequest(CoreModelBase):
    title: str
    raw_text: str
    request: dict

class PatchActionRequest(CoreModelBase):
    title: str

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

class PatchThreadActionRequest(CoreModelBase):
    show_question: Optional[bool] = None
    show_answer: Optional[bool] = None
