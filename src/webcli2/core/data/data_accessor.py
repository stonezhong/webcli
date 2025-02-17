from typing import List, Dict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import Engine, select, delete, func
from webcli2.core.data.db_models import DBThread, DBThreadAction, DBAction, DBActionResponseChunk, DBUser
from webcli2.core.data.models import User, Thread, ThreadSummary, ThreadAction, Action, ActionResponseChunk

#############################################################
# Get the current UTC time
#############################################################
def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DataError(Exception):
    pass

class ObjectNotFoun(DataError):
    object_type: str
    object_id: int

    def __init__(self, object_type:str, object_id:int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_type = object_type
        self.object_id = object_id
    
    def __str__(self):
        return f"ObjectNotFound(object_type=\"{self.object_type}\", object_id={self.object_id})"

class AccessDenied(DataError):
    pass
   
class DataAccessor:
    session: Session

    def __init__(self, session:Session):
        self.session = session

    def create_user(self, *, email:str, password_hash:str) -> User:
        """Create a new user.
        """
        db_user = DBUser(
            is_active = True,
            email = email,
            password_version = 1,
            password_hash = password_hash
        )
        self.session.add(db_user)
        self.session.commit()
        return User.from_db(db_user)


    def list_threads(self, *, user:User) -> List[ThreadSummary]:
        """List all thread owned by user.
        """
        db_threads = self.session.scalars(
            select(DBThread)\
                .join(DBThread.user)\
                .where(DBThread.user_id == user.id)\
                .order_by(DBThread.id)
        )
        return [
            ThreadSummary.from_db(db_thread) for db_thread in db_threads
        ]

    def get_thread(self, thread_id:int, *, user:User) -> Thread:
        """Retrive a thread.
        """
        db_thread = self.session.get(DBThread, thread_id)
        if db_thread is None or db_thread.user_id != thread_id:
            raise ObjectNotFoun("Thread", thread_id)

        thread = Thread.from_db(db_thread) # need to fill in thread_actions

        thread_actions: List[ThreadAction] = []
        for db_thread_action in self.session.scalars(
            select(DBThreadAction)\
                .join(DBThreadAction.action)\
                .where(DBThreadAction.thread_id == thread_id)\
                .order_by(DBThreadAction.display_order)
        ):
            db_action = db_thread_action.action

            db_response_chunks = self.session.scalars(
               select(DBActionResponseChunk)\
                    .where(DBActionResponseChunk.action_id == db_thread_action.action_id)\
                    .order_by(DBActionResponseChunk.order)
            )

            response_chunks = [
                ActionResponseChunk.from_db(db_action_response_chunk)
                for db_action_response_chunk in db_response_chunks
            ]

            action = Action.from_db(db_action)
            action.response_chunks = response_chunks
            thread_actions.append(
                ThreadAction(
                    id = db_thread_action.id,
                    thread_id = thread_id,
                    action = action,
                    display_order = db_thread_action.display_order,
                    show_question = db_thread_action.show_question,
                    show_answer = db_thread_action.show_answer
                )
            )
        
        thread = Thread(
            id = db_thread.id,
            user = User.from_db(db_thread.user),
            created_at = db_thread.created_at,
            title = db_thread.title,
            description = db_thread.description,
            thread_actions = thread_actions
        )
        return thread
        
            
    def create_thread(self, *, title:str, description:str, user:User) -> Thread:
        """Create a new thread.
        """
        db_thread = DBThread(
            user_id = user.id,
            created_at = get_utc_now(),
            title = title,
            description = description
        )
        self.session.add(db_thread)
        self.session.commit()
        thread = self.get_thread(db_thread.id, user=user)
        return thread

    def create_action(self, *, handler_name:str, request:dict, title:str, raw_text:str, user:User) -> Thread:
        """Create a new action.
        """
        db_action = DBAction(
            user_id = user.id,
            handler_name = handler_name,
            is_completed = False,
            created_at = get_utc_now(),
            completed_at = None,
            request = request,
            title = title,
            raw_text = raw_text
        )
        self.session.add(db_action)
        self.session.commit()

        return self.get_action(db_action.id, user=user)
    
    def get_action(self, action_id:int, *, user:User) -> Action:
        """Retrieve an action.
        """
        db_action = self.session.get(DBAction, action_id)
        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFoun("Action", action_id)
        
        action = Action.from_db(db_action)
        action.response_chunks = [
            ActionResponseChunk.from_db(db_action_response_chunk) for db_action_response_chunk in self.session.scalars(
                select(DBActionResponseChunk)\
                    .where(DBThreadAction.action_id == action_id)
            )
        ]
        return action
    
    def append_action_to_thread(self, *, thread_id:int, action_id:int, user:User) -> ThreadAction:
        """Append an action to the end of a thread.
        """
        db_action = self.session.get(DBAction, action_id)
        db_thread = self.session.get(DBThread, thread_id)

        if thread_id is None:
            raise ObjectNotFoun("Thread", thread_id)

        if db_action is None:
            raise ObjectNotFoun("Action", action_id)
        
        if db_thread.user_id != user.id:
            raise AccessDenied()
        
        if db_action.user_id != user.id:
            raise AccessDenied()
        
        old_max_display_order = self.session.scalars(
            select(
                func.max(DBThreadAction.display_order)
            ).where(DBThreadAction.thread_id == thread_id)
        ).one()
        if old_max_display_order is None:
            display_order = 1
        else:
            display_order = old_max_display_order + 1
       
        db_thread_action = DBThreadAction(
            thread_id = thread_id,
            action_id = action_id,
            display_order = display_order,
            show_question = False,
            show_answer = True
        )
        self.session.add(db_thread_action)
        self.session.commit()

        thread_action = ThreadAction(
            id = db_thread_action.id,
            thread_id = db_thread_action.thread_id,
            action = self.get_action(db_thread_action.action_id, user=user),
            display_order = db_thread_action.display_order,
            show_question = db_thread_action.show_question,
            show_answer = db_thread_action.show_answer
        )
        return thread_action

    def append_response_to_action(
        self, 
        action_id:int, 
        *, 
        mime:str, 
        text_content:Optional[str] = None, 
        binary_content:Optional[bytes] = None, 
        user:User
    ) -> ThreadAction:
        """Append an action to the end of a thread.
        """
        db_action = self.session.get(DBAction, action_id)
        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFoun("Action", action_id)
        
        old_max_order = self.session.scalars(
            select(
                func.max(DBActionResponseChunk.order)
            ).where(DBActionResponseChunk.action_id == action_id)
        ).one()
        if old_max_order is None:
            order = 1
        else:
            order = old_max_order + 1

        db_action_response_chunk = DBActionResponseChunk(
            action_id = action_id,
            order = order,
            mime = mime,
            text_content = text_content,
            binary_content = binary_content
        )
        self.session.add(db_action_response_chunk)
        self.session.commit()

        action_response_chunk = ActionResponseChunk.from_db(
            db_action_response_chunk,
        )
        return action_response_chunk

    def remove_action_from_thread(
        self, 
        *,
        action_id:int, 
        thread_id:int,
        user:User
    ) -> bool:
        """Remove an action from a thread, it does not delete the action.

        Returns:
            bool: True if the action is removed, False if the action was not part of the thread
        """
        db_action = self.session.get(DBAction, action_id)
        db_thread = self.session.get(DBThread, thread_id)

        if thread_id is None:
            raise ObjectNotFoun("Thread", thread_id)

        if db_action is None:
            raise ObjectNotFoun("Action", action_id)
        
        if db_thread.user_id != user.id:
            raise AccessDenied()
        
        if db_action.user_id != user.id:
            raise AccessDenied()
        
        result = self.session.execute(
            delete(DBThreadAction)\
                .where(DBThreadAction.thread_id == thread_id)\
                .where(DBThreadAction.action_id == action_id)
        )
        deleted_rows = result.rowcount
        self.session.commit()
        return deleted_rows > 0


    def delete_thread(
        self, 
        thread_id:int,
        *,
        user:User
    ):
        """Delete a thread.

        """
        db_thread = self.session.get(DBThread, thread_id)

        if thread_id is None:
            raise ObjectNotFoun("Thread", thread_id)

        if db_thread.user_id != user.id:
            raise AccessDenied()
        
        self.session.execute(
            delete(DBThreadAction)\
                .where(DBThreadAction.thread_id == thread_id)
        )
        self.session.execute(
            delete(DBThread)\
                .where(DBThread.id == thread_id)
        )
        self.session.commit()

