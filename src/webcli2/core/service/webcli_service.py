from __future__ import annotations  # Enables forward declaration

import logging
logger = logging.getLogger(__name__)

from typing import Optional, List, Dict, Any
import uuid
from concurrent.futures import ThreadPoolExecutor
from asyncio import get_event_loop, AbstractEventLoop
from copy import copy

from sqlalchemy.orm import Session
import bcrypt
import jwt
from pydantic import BaseModel
from sqlalchemy import Engine

from webcli2.core.data import User, Thread, Action, DataAccessor, ThreadAction
import webcli2.action_handlers.action_handler as action_handler

class ServiceError(Exception):
    pass

class InvalidJWTTOken(ServiceError):
    pass

class NoHandler(ServiceError):
    pass

class JWTTokenPayload(BaseModel):
    email: str
    password_version: int
    sub: str
    uuid: str

##############################################################
# APIs
#     create_user
#     get_user_from_jwt_token
#     login_user
#     generate_user_jwt_token
# 
#     list_threads
#     create_thread
#     get_thread
#     patch_thread
#     delete_thread
#     remove_action_from_thread
#     patch_action
#     patch_thread_action
#     
##############################################################

##############################################################
# Given incoming action
# During the phase we are looking for action handlers, we run in IO thread (which is an async thread)
# Once we've identified a handler, we will create action, finish the HTTP request, then let the action 
# handler to handle it in a thread pool
##############################################################


class WebCLIService:
    public_key:str                                  # for JWT
    private_key:str                                 # for JWT
    users_home_dir: str                             # The parent directory for all user's home dir
    db_engine: Engine                               # SQLAlchemy engine
    executor: Optional[ThreadPoolExecutor]          # A thread pool
    event_loop: Optional[AbstractEventLoop]         # The current main loop
    action_handlers: Dict[str, action_handler.ActionHandler]

    def __init__(
        self, 
        *, 
        users_home_dir:str,
        public_key:str, 
        private_key:str, 
        db_engine:Engine,
        action_handlers:Dict[str, action_handler.ActionHandler]           
    ):
        self.public_key = public_key
        self.private_key = private_key
        self.users_home_dir = users_home_dir
        self.db_engine = db_engine
        self.executor = None
        self.event_loop = None
        self.action_handlers = copy(action_handlers)

    def startup(self):
        log_prefix = "WebCLIService.startup"
        
        # TODO: maybe I should limit the thread number
        self.require_shutdown = False
        self.executor = ThreadPoolExecutor()
        self.event_loop = get_event_loop()

        # Initialize all action handlers
        for action_handler_name, action_handler in self.action_handlers.items():
            # TODO: if an action failed to startup, remove it since it may not handle
            #       request properly
            try:
                logger.info(f"{log_prefix}: startup action handler, name={action_handler_name},  {action_handler}")
                action_handler.startup(self)
            except Exception:
                # we will tolerate if action handler failed to startup
                logger.error(f"{log_prefix}: action handler startup exception", exc_info=True)
        logger.info(f"{log_prefix}: all action handlers are started")

    def shutdown(self):
        log_prefix = "WebCLIService.shutdown"
        assert self.require_shutdown == False
        self.require_shutdown = True

        # shutdown all action handler
        for action_handler_name, action_handler in self.action_handlers.items():
            try:
                logger.debug(f"{log_prefix}: shutdown action handler, name={action_handler_name},  {action_handler}")
                action_handler.shutdown()
            except Exception:
                # we will tolerate if action handler failed to shutdown
                logger.error(f"{log_prefix}: action handler shutdown exception", exc_info=True)
        logger.info(f"{log_prefix}: all action handlers are shutdown")
        # TODO: what if some request are stuck, shall we hang on shutdown?
        self.executor.shutdown(wait=True)

    def _hash_password(self, password:str) -> str:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed_password.decode("utf-8")

    def _discover_action_handler(self, request:Any):
        for action_handler_name, action_handler in self.action_handlers.items():
            if action_handler.can_handle(request):
                logger.debug(f"WebCLIService._discover_action_handler: found action handler, name={action_handler_name}")
                return action_handler_name, action_handler
        logger.debug(f"WebCLIService._discover_action_handler: cannot find action handler for this request")
        return None, None
    
    def _action_handler_handle_proxy(self, action_handler, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        """ This is the proxy for action_handler.handle
        The purpose is to capture exception and log
        """
        try:
            action_handler(action_id, request, user, action_handler_user_config, service=self)
            self.complete_action(action_id, user=user)
            logger.debug(f"Action handler {action_handler} successfully handled an action({action_id})")
        except Exception:
            logger.exception(f"Action handler {action_handler} failed when handing action({action_id})")

    ##############################################################
    # Below are APIs
    ##############################################################
    def create_user(self, *, email:str, password:str) -> User:
        """ Create a new user.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            user = da.create_user(
                email = email, 
                password_hash=self._hash_password(password)
            )
            return user

    def get_user_from_jwt_token(self, jwt_token:str) -> User:
        """ Get user from JWT token.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            try:
                payload = jwt.decode(jwt_token, self.public_key, algorithms=["RS256"])
            except jwt.exceptions.InvalidSignatureError as e:
                raise InvalidJWTTOken() from e
            
            jwt_token_payload = JWTTokenPayload.model_validate(payload)
            user_id = int(jwt_token_payload.sub)
            user = da.get_user(user_id)
            return user

        
    def login_user(self, *, email:str, password:str) -> Optional[User]:
        """ Login user.
        Returns:
            None if user failed to login. Otherwise, a user object is returned.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            user = da.find_user_by_email(email)
            if user is None:
                return None
            
            if bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8")):
                return user
            else:
                return None
    
    def generate_user_jwt_token(self, user:User)->str:
        """ Generate user JWT token.
        Returns:
            None if user failed to login. Otherwise, a user object is returned.
        """
        payload = JWTTokenPayload(
            email = user.email,
            password_version = user.password_version,
            sub = str(user.id),
            uuid = str(uuid.uuid4())
        )
        jwt_token = jwt.encode(
            payload.model_dump(mode='json'), 
            self.private_key, 
            algorithm="RS256"
        )
        return jwt_token
    
    def list_threads(self, *, user:User) -> List[Thread]:
        """List all thread owned by user.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.list_threads(user=user)

    def create_thread(self, *, title:str, description:str, user:User) -> Thread:
        """Create a new thread.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.create_thread(title=title, description=description, user=user)

    def get_thread(self, thread_id:int, *, user:User) -> Thread:
        """Retrive a thread.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.get_thread(thread_id, user=user)

    def patch_thread(
        self, 
        thread_id:int, 
        *, 
        user:User,
        title:Optional[str]=None, 
        description:Optional[str]=None
    ) -> Thread:
        """Update a thread's title and/or description.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.patch_thread(thread_id, title=title, description=description, user=user)

    def create_action(self, *, request:dict, title:str, raw_text:str, user:User) -> Action:
        """Create a new action.
        """
        action_handler_name, action_handler = self._discover_action_handler(request)
        if action_handler_name is None:
            raise NoHandler()
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            # we are going to let action handler to handle this action in a thread pool
            # and finish this API without waiting for the action handler to complete handling the request
            action = da.create_action(
                handler_name=action_handler_name, 
                request=request, 
                title=title, 
                raw_text=raw_text, 
                user=user
            )
            action_handler_user_config = self.get_action_handler_user_config(
                action_handler_name=action_handler_name,
                user=user
            )
            # Invoke handler in thread pool, and no wait
            self.executor.submit(
                self._action_handler_handle_proxy,
                action_handler.handle, 
                action.id, 
                request, 
                user, 
                action_handler_user_config
            )
            logger.debug(f"WebCLIService.create_action: submit a thread task for {action_handler_name} to handle an action")
            return action

    def delete_thread(self, thread_id:int, *, user:User):
        """Delete a thread.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.delete_thread(thread_id, user=user)

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
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.remove_action_from_thread(action_id=action_id, thread_id=thread_id, user=user)
        
    def patch_action(self, action_id:int, *, user:User, title:Optional[str]=None) -> Action:
        """Update action's title.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.patch_action(action_id, user=user, title=title)

    def append_action_to_thread(self, *, thread_id:int, action_id:int, user:User) -> ThreadAction:
        """Append an action to the end of a thread.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.append_action_to_thread(thread_id=thread_id, action_id=action_id, user=user)

    def append_response_to_action(
        self, 
        action_id:int, 
        *, 
        mime:str, 
        text_content:Optional[str] = None, 
        binary_content:Optional[bytes] = None, 
        user:User
    ) -> ThreadAction:
        """Append an response chunk to the end of a action.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.append_response_to_action(
                action_id, 
                mime=mime, 
                text_content=text_content, 
                binary_content=binary_content, 
                user=user
            )


    def patch_thread_action(
        self, 
        thread_id:int, 
        action_id:int, 
        *, 
        user:User,
        show_question:Optional[bool]=None, 
        show_answer:Optional[bool]=None
    ) -> ThreadAction:
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.patch_thread_action(
                thread_id, 
                action_id, 
                user=user, 
                show_question=show_question, 
                show_answer=show_answer
            )

    def get_action_handler_user_config(
        self,
        *,
        action_handler_name:str,
        user:User 
    ) -> dict:
        """Get user configuration for a action handler.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.get_action_handler_user_config(action_handler_name=action_handler_name, user=user)
    
    def complete_action(self, action_id:int, *, user:User) -> Action:
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.complete_action(action_id, user=user)
