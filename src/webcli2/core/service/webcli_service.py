from __future__ import annotations  # Enables forward declaration

import logging
logger = logging.getLogger(__name__)

from typing import Optional, List, Dict, Any
import uuid
from concurrent.futures import ThreadPoolExecutor
from asyncio import get_event_loop, AbstractEventLoop, run_coroutine_threadsafe
from copy import copy
import json
import time
import os

from sqlalchemy.orm import Session
import bcrypt
import jwt
from pydantic import BaseModel
from sqlalchemy import Engine
from fastapi import WebSocket, WebSocketDisconnect

from webcli2.core.data import User, Thread, Action, DataAccessor, ThreadAction, ActionResponseChunk, create_all_tables as cat
import webcli2.action_handlers.action_handler as action_handler
from .notifications import NotificationManager, pop_notification, Notification

WEB_SOCKET_PING_INTERVAL = 20  # in seconds

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
    resource_dir:str                                # The directory to store all binary_output for action response chunks
    db_engine: Engine                               # SQLAlchemy engine
    executor: Optional[ThreadPoolExecutor]          # A thread pool
    event_loop: Optional[AbstractEventLoop]         # The current main loop
    action_handlers: Dict[str, action_handler.ActionHandler]
    nm: NotificationManager

    def __init__(
        self, 
        *, 
        users_home_dir:str,
        resource_dir:str,
        public_key:str, 
        private_key:str, 
        db_engine:Engine,
        action_handlers:Dict[str, action_handler.ActionHandler]           
    ):
        self.public_key = public_key
        self.private_key = private_key
        self.users_home_dir = users_home_dir
        self.resource_dir = resource_dir
        self.db_engine = db_engine
        self.executor = None
        self.event_loop = None
        self.action_handlers = copy(action_handlers)
        self.nm = NotificationManager()

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
            ret = action_handler(action_id, request, user, action_handler_user_config)
            if ret:
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
            user = da.get_user_by_email(email)
            if user is None:
                return None
            
            if bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
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

    def create_thread_action(self, *, request:dict, thread_id:int, title:str, raw_text:str, user:User) -> ThreadAction:
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
            thread_aciton = da.append_action_to_thread(thread_id=thread_id, action_id=action.id, user=user)

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
            return thread_aciton

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

    def complete_action(self, action_id:int, *, user:User) -> Action:
        """Set an action to be completed.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            action = da.complete_action(action_id, user=user)

            thread_ids = da.get_thread_ids_for_action(action_id)

            completed_at = action.model_dump(mode="json")["completed_at"]
            event = {
                "type": "action-completed",
                "action_id": action_id,
                "completed_at": completed_at
            }

            notifications: List[Notification] = [
                Notification(
                    topic_name=f"topic-{thread_id}", 
                    event = event
                ) for thread_id in thread_ids
            ]

            run_coroutine_threadsafe(
                self.nm.publish_notifications(notifications),
                self.event_loop
            )
        
            return action

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
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            action_response_chunk = da.append_response_to_action(
                action_id, 
                mime=mime, 
                text_content=text_content, 
                binary_content=binary_content, 
                user=user
            )

            # For binary content, if we know the mime type, we will save the content
            # so it can be referenced by output chunk
            if binary_content is not None:
                if mime == "image/png":
                    fileext = "png"
                else:
                    fileext = None
                
                if fileext is not None:
                    resource_dir = os.path.join(self.resource_dir, str(action_id))
                    os.makedirs(resource_dir, exist_ok=True)
                    filename = os.path.join(resource_dir, f"{str(action_response_chunk.id)}.{fileext}")
                    with open(filename, "wb") as f:
                        f.write(binary_content)

            thread_ids = da.get_thread_ids_for_action(action_id)
            event = {
                "type": "action-response-chunk",
                "id": action_response_chunk.id,
                "action_id": action_id,
                "order": action_response_chunk.order,
                "mime": action_response_chunk.mime,
                "text_content": action_response_chunk.text_content
            }

            notifications: List[Notification] = [
                Notification(topic_name=f"topic-{thread_id}", event = event) for thread_id in thread_ids
            ]

            run_coroutine_threadsafe(
                self.nm.publish_notifications(notifications),
                self.event_loop
            )

            return action_response_chunk


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
    

    def set_action_handler_user_config(
        self,
        *,
        action_handler_name:str,
        user:User,
        config:dict
    ):
        """Set user configuration for a action handler.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.set_action_handler_user_config(action_handler_name=action_handler_name, user=user, config=config)

    def get_action_user(self, action_id:int) -> Optional[User]:
        """Get user for the action.
        """
        with Session(self.db_engine) as session:
            da = DataAccessor(session)
            return da.get_action_user(action_id)

    #######################################################################
    # This is called by web socket endpoint from fastapi
    # Here is an example
    #
    # @app.websocket("/ws")
    # async def websocket_endpoint(websocket: WebSocket):
    #     web_socket_connection_manager.websocket_endpoint(websocket)
    #
    #######################################################################
    async def websocket_endpoint(self, websocket: WebSocket):
        log_prefix = "WebCLIService.websocket_endpoint"

        logger.debug(f"{log_prefix}: waiting for incoming connection")
        await websocket.accept()
        logger.debug(f"{log_prefix}: client is connected")

        # client need to report it's client ID in the first place
        data = await websocket.receive_text()
        logger.debug(f"{log_prefix}: client information is: {data}")
        client_id:Optional[str] = None
        thread_id:Optional[int] = None
        try:
            json_data = json.loads(data)
            if isinstance(json_data, dict):
                client_id = json_data.get("client_id")
                if not isinstance(client_id, str):
                    client_id = None
                thread_id = json_data.get("thread_id")
                if not isinstance(thread_id, int):
                    thread_id = None
        except json.decoder.JSONDecodeError:
            pass

        if client_id is None or thread_id is None:
            logger.debug(f"{log_prefix}: client information is corrupted, quit")
            await websocket.close(code=1000, reason="Client ID and Thread ID not provided")
            return

        topic_name = f"topic-{thread_id}"
        q = await self.nm.subscribe(topic_name, client_id)
          
        try:
            last_ping_time:float = None
            while True:
                # need to ping client if needed
                now = time.time()
                if last_ping_time is None or now - last_ping_time >= WEB_SOCKET_PING_INTERVAL:
                    last_ping_time = now
                    await websocket.send_text("ping")

                r = await pop_notification(q, 10)
                if r is None:
                    # no notification
                    continue

                await websocket.send_text(json.dumps(r))
                logger.debug(f"{log_prefix}: notify client({client_id}) on topic({topic_name}) via websocket")
        except WebSocketDisconnect:
            await self.nm.unsubscribe(topic_name, client_id)
            logger.debug(f"{log_prefix}: client({client_id}) disconnected")

    def get_action_handler(self, action_handler_name:str) -> Optional[action_handler.ActionHandler]:
        return self.action_handlers.get(action_handler_name)

    def create_all_tables(self):
        return cat(self.db_engine)
