from typing import List, Dict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import Engine, select, delete, func
from webcli2.core.data.db_models import DBThread, DBThreadAction, DBAction, DBActionResponseChunk, DBUser, DBActionHandlerConfiguration
from webcli2.core.data.models import User, Thread, ThreadSummary, ThreadAction, Action, ActionResponseChunk

#############################################################
# Get the current UTC time
#############################################################
def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DataError(Exception):
    pass

class ObjectNotFound(DataError):
    object_type: Optional[str]
    object_id: Optional[int]
    message: Optional[str]

    def __init__(
        self, 
        *args, 
        object_type:Optional[str]=None, 
        object_id:Optional[int]=None, 
        message:Optional[str]=None, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.object_type = object_type
        self.object_id = object_id
        self.message = message
    
    def __str__(self):
        message = "Object not found: "
        if self.object_type is not None:
            message += f"object_type=\"{self.object_type}\", "
        if self.object_id is not None:
            message += f"object_id={self.object_id}, "
        if self.message is not None:
            message += self.message
        return message
 
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

    def get_user(self, user_id:int) -> User:
        """Get a user by ID.
        """
        db_user = self.session.get(DBUser, user_id)
        if db_user is None:
            raise ObjectNotFound(object_type="User", object_id=user_id)
        
        return User.from_db(db_user)

    def get_user_by_email(self, email:str) -> User:
        """Get a user by email.
        """
        db_user = self.session.scalars(
            select(DBUser)\
                .where(DBUser.email == email)
        ).one_or_none()
        if db_user is None:
            raise ObjectNotFound(object_type="User", message=f"email=\"{email}\"")
        
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
            raise ObjectNotFound(object_type="Thread", object_id=thread_id)

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

    def patch_thread(
        self, 
        thread_id:int, 
        *, 
        user:User,
        title:Optional[str] = None, 
        description:Optional[str] = None
    ) -> Thread:
        """Update thread title and/or description.
        """
        db_thread = self.session.get(DBThread, thread_id)
        if db_thread is None or db_thread.user_id != thread_id:
            raise ObjectNotFound(object_type="Thread", object_id=thread_id)
        
        updated_fields = 0
        if title is not None:
            db_thread.title = title
            updated_fields += 1
        if description is not None:
            db_thread.description = description
            updated_fields += 1
        
        if updated_fields > 0:
            self.session.add(db_thread)
            self.session.commit()

        return self.get_thread(thread_id, user=user)
        

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
            raise ObjectNotFound(object_type="Action", object_id=action_id)
        
        action = Action.from_db(db_action)
        action.response_chunks = [
            ActionResponseChunk.from_db(db_action_response_chunk) for db_action_response_chunk in self.session.scalars(
                select(DBActionResponseChunk)\
                    .where(DBActionResponseChunk.action_id == action_id)
            )
        ]
        return action

    def patch_action(self, action_id:int, *, user:User, title:Optional[str]=None) -> Action:
        """Update action's title.
        """
        db_action = self.session.get(DBAction, action_id)
        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFound(object_type="Action", object_id=action_id)

        if title is not None:
            db_action.title = title
            self.session.add(db_action)
            self.session.commit()
        
        return self.get_action(action_id, user=user)

    def complete_action(self, action_id:int, *, user:User) -> Action:
        """Set an action to be completed.
        """
        db_action = self.session.get(DBAction, action_id)
        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFound(object_type="Action", object_id=action_id)

        db_action.is_completed = True
        db_action.completed_at = get_utc_now()
        self.session.add(db_action)
        self.session.commit()
        
        return self.get_action(action_id, user=user)

    def append_action_to_thread(self, *, thread_id:int, action_id:int, user:User) -> ThreadAction:
        """Append an action to the end of a thread.
        """
        db_thread = self.session.get(DBThread, thread_id)
        db_action = self.session.get(DBAction, action_id)

        if db_thread is None or db_thread.user_id != user.id:
            raise ObjectNotFound(object_type="Thread", object_id=thread_id)

        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFound(object_type="Action", object_id=action_id)
               
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
    ) -> ActionResponseChunk:
        """Append an response chunk to the end of a action.
        """
        db_action = self.session.get(DBAction, action_id)
        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFound(object_type="Action", object_id=action_id)
        
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
        db_thread = self.session.get(DBThread, thread_id)
        db_action = self.session.get(DBAction, action_id)

        if db_thread is None or db_thread.user_id != user.id:
            raise ObjectNotFound(object_type="Thread", object_id=thread_id)

        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFound(object_type="Action", object_id=action_id)
        
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

        if db_thread is None or db_thread.user_id != user.id:
            raise ObjectNotFound(object_type="Thread", object_id=thread_id)

        self.session.execute(
            delete(DBThreadAction)\
                .where(DBThreadAction.thread_id == thread_id)
        )
        self.session.execute(
            delete(DBThread)\
                .where(DBThread.id == thread_id)
        )
        self.session.commit()

    def patch_thread_action(
        self, 
        thread_id:int, 
        action_id:int, 
        *, 
        user:User,
        show_question:Optional[bool]=None, 
        show_answer:Optional[bool]=None
    ) -> ThreadAction:
        """Update thread action's show_question and/or show_answer.
        """
        db_thread = self.session.get(DBThread, thread_id)
        if db_thread is None or db_thread.user_id != user.id:
            raise ObjectNotFound(object_type="Thread", object_id=thread_id)

        db_action = self.session.get(DBAction, action_id)
        if db_action is None or db_action.user_id != user.id:
            raise ObjectNotFound(object_type="Action", object_id=action_id)

        db_thread_action = self.session.scalars(
            select(DBThreadAction)\
                .where(DBThreadAction.thread_id == thread_id)\
                .where(DBThreadAction.action_id == action_id)
        ).one_or_none()
        if db_thread_action is None:
            raise ObjectNotFound(object_type="ThreadAction", message=f"thread_id={thread_id}, action_id={action_id}")

        updated_fields = 0
        if show_question is not None:
            db_thread_action.show_question = show_question
            updated_fields += 1
        if show_answer is not None:
            db_thread_action.show_answer = show_answer
            updated_fields += 1
        
        if updated_fields > 0:
            self.session.add(db_thread_action)
            self.session.commit()

        thread_action = ThreadAction(
            id = db_thread_action.id,
            thread_id = db_thread_action.thread_id,
            action = self.get_action(db_thread_action.action_id, user=user),
            display_order=db_thread_action.display_order,
            show_question=db_thread_action.show_question,
            show_answer=db_thread_action.show_answer
        )
        return thread_action

    def get_action_handler_user_config(
        self,
        *,
        action_handler_name:str,
        user:User
    ) -> dict:
        """Get user configuration for a action handler.
        """
        db_ahc = self.session.scalars(
            select(DBActionHandlerConfiguration)\
                .where(DBActionHandlerConfiguration.user_id == user.id)\
                .where(DBActionHandlerConfiguration.action_handler_name == action_handler_name)
        ).one_or_none()
        if db_ahc is None:
            return {}
        if db_ahc.configuration is None:
            return {}
        return db_ahc.configuration

    def set_action_handler_user_config(
        self,
        *,
        action_handler_name:str,
        user:User,
        config:dict
    ):
        """Set user configuration for a action handler.
        """
        db_ahc = self.session.scalars(
            select(DBActionHandlerConfiguration)\
                .where(DBActionHandlerConfiguration.user_id == user.id)\
                .where(DBActionHandlerConfiguration.action_handler_name == action_handler_name)
        ).one_or_none()
        if db_ahc is None:
            db_ahc = DBActionHandlerConfiguration(
                action_handler_name = action_handler_name,
                user_id = user.id,
                created_at = get_utc_now(),
                configuration = config 
            )
        else:
            db_ahc.configuration = config
            db_ahc.updated_at = get_utc_now()

        self.session.add(db_ahc)
        self.session.commit()

    def get_thread_ids_for_action(self, action_id:int) -> List[int]:
        """Get list of threads that has this action.

        Note: We are not checking user, since an action can potentially be part of multiple
              threads owned by different users.
        """
        return [db_thread_action.thread_id for db_thread_action in self.session.scalars(
            select(DBThreadAction)\
                .where(DBThreadAction.action_id == action_id)
        )]

    def get_action_user(self, action_id:int) -> Optional[User]:
        """Get user for the action.
        """
        db_action = self.session.get(DBAction, action_id)
        if db_action is None:
            return None
        return User.from_db(db_action.user)
