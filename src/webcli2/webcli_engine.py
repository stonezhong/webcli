from __future__ import annotations  # Enables forward declaration

import logging
logger = logging.getLogger(__name__)

from typing import Dict, Tuple, Any, List, Optional
from datetime import datetime, timezone
from asyncio import Event, get_event_loop, AbstractEventLoop
import enum
import os
from copy import copy
from concurrent.futures import ThreadPoolExecutor
import threading
import asyncio
import uuid
from contextvars import ContextVar

from pydantic import BaseModel
import bcrypt
import jwt

from sqlalchemy.orm import Session
from sqlalchemy import Engine, select, delete
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func

from webcli2.db_models import DBAction, DBActionHandlerConfiguration, DBUser, DBThread, DBThreadAction
from webcli2.models import Action, ActionHandlerConfiguration, User, JWTTokenPayload, Thread, ThreadAction
from webcli2.models.apis import CreateThreadRequest, CreateActionRequest, PatchActionRequest, \
    PatchThreadActionRequest, PatchThreadRequest
from webcli2.websocket import WebSocketConnectionManager
from webcli2.apilog import log_api_enter, log_api_exit
from webcli2.webcli.output import CLIOutput
import webcli2.action_handlers.action_handler as action_handler


class TheradContext:
    user:User
    client_id:Optional[str]
    action_id:int
    stdout: CLIOutput

    def __init__(self, user:User, action_id:int):
        self.user = user
        self.client_id = None
        self.action_id = action_id
        self.stdout = CLIOutput(chunks=[])

thread_context_var = ContextVar("thread_context", default=None)

#############################################################
# Get the current UTC time
#############################################################
def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# this is only for logging
def action_to_str(action:Optional[Action]) -> str:
    return "None" if action is None else f"Action(id={action.id})"

# Status code for WebCLIEngine API calls
class WebCLIEngineStatus(enum.Enum):
    OK                      = 0
    DB_FAILED               = 1 # database failure
    NOT_FOUND               = 2 # you cannot update, monior, complete an action since the action does not exist
    ACTION_COMPLETED        = 3 # you cannot update an action since the action has been completed
    TIMEDOUT                = 4 # wait on an action to completed timed out
    SHUTDOWN_IN_PROGRESS    = 5 # we cannot service you since we are shutting down
    NO_HANDLER              = 6 # we cannot find a handler to handle this action

#############################################################
# Tracks an asynchronous call
#############################################################
class AsyncCall:
    return_value: Any
    event: Event
    event_loop: AbstractEventLoop

    def __init__(self, event_loop:AbstractEventLoop):
        self.return_value = None
        self.event = Event()
        self.event_loop = event_loop
    
    # make the call finished
    def finish(self, *, return_value:Any=None):
        self.return_value = return_value
        self.event_loop.call_soon_threadsafe(self.event.set)
    
    ####################################################################
    # Wait for the async call to finish and retrieve the return value
    ####################################################################
    async def async_await_return(self) -> Any:
        await self.event.wait()
        return self.return_value


class UserManager:
    db_engine: Engine
    public_key:str
    private_key:str

    def __init__(self, *, db_engine:Engine, private_key:str, public_key:str):
        self.db_engine = db_engine
        self.private_key = private_key
        self.public_key = public_key

    def hash_password(self, password:str) -> str:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed_password.decode("utf-8")

    def verify_password(self, plain_password:str, hashed_password:str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    #######################################################################
    # Create a new User
    # It may fail, for example, duplicate email, in case of failure, it returns None
    # Otherwise, it returns the newly created user.
    #######################################################################
    def create_user(self, email, password) -> Optional[User]:
        with Session(self.db_engine) as session:
            try:
                with session.begin():
                    db_user = DBUser(
                        is_active = True,
                        email = email,
                        password_version = 1,
                        password_hash = self.hash_password(password),
                    )
                    session.add(db_user)
            except IntegrityError:
                logger.debug(f"UserManager.create_user: cannot create user due to IntegrityError")
                db_user = None
            user = None if db_user is None else User.create(db_user)
        return user
    
    def create_jwt_token(self, user:User) ->str:
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

    #######################################################################
    # Verify a JWT token and extract token payload from it
    # If the JWT token failed the validation, it returns None
    #######################################################################
    def extract_payload_from_jwt_token(self, jwt_token:str) -> JWTTokenPayload:
        try:
            payload = jwt.decode(jwt_token, self.public_key, algorithms=["RS256"])
        except jwt.exceptions.InvalidSignatureError:
            return None
        return JWTTokenPayload.model_validate(payload)

    #######################################################################
    # Get user from jwt token
    # If the JWT token failed the validation, it returns None
    #######################################################################
    def get_user_from_jwt_token(self, jwt_token:str) -> User:
        with Session(self.db_engine) as session:
            with session.begin():
                payload = self.extract_payload_from_jwt_token(jwt_token)
                if payload is None:
                    return None
                db_user = session.get(DBUser, int(payload.sub))
                return User.create(db_user)
    
    #######################################################################
    # If email and password is correct, it returns a User model
    # Otherwise, it returns None
    #######################################################################
    def login(self, email, password) -> Optional[User]:
        with Session(self.db_engine) as session:
            with session.begin():
                db_users = list(session.query(DBUser)\
                    .filter(DBUser.email == email)\
                    .all())
                users = [User.create(db_user) for db_user in db_users]
        
        assert len(users) in (0, 1)
        if len(users) == 0:
            return None
        
        user = users[0]
        return user if self.verify_password(password, user.password_hash) else None

class WebCLIEngine:
    users_home_dir: str                             # The parent directory for all user's home dir
    db_engine: Engine                               # SQLAlchemy engine
    wsc_manager: WebSocketConnectionManager         # Web Socket Connection Manager
    executor: Optional[ThreadPoolExecutor]          # A thread pool
    event_loop: Optional[AbstractEventLoop]         # The current main loop
    lock: threading.Lock                            # a global lock
    require_shutdown: Optional[bool]                # True if shutdown has been requested
    action_handlers: Dict[str, action_handler.ActionHandler]       # action handlers map

    def __init__(
        self, 
        *, 
        users_home_dir:str,
        db_engine:Engine, 
        wsc_manager:WebSocketConnectionManager, 
        action_handlers:Dict[str, action_handler.ActionHandler]
    ):
        log_prefix = "WebCLIEngine.__init__"
        log_api_enter(logger, log_prefix)
        self.users_home_dir = users_home_dir
        self.db_engine = db_engine
        self.wsc_manager = wsc_manager
        self.executor = None
        self.event_loop = None
        self.lock = threading.Lock()
        self.require_shutdown = None
        self.action_handlers = copy(action_handlers)
        os.makedirs(self.users_home_dir, exist_ok=True)
        log_api_exit(logger, log_prefix)


    def startup(self):
        log_prefix = "WebCLIEngine.startup"
        # TODO: maybe I should limit the thread number
        log_api_enter(logger, log_prefix)
        self.require_shutdown = False
        self.executor = ThreadPoolExecutor()

        self.event_loop = get_event_loop()
        logger.info(f"{log_prefix}: event loop is {self.event_loop}")

        # register all action handler
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
        log_api_exit(logger, log_prefix)

    def shutdown(self):
        log_prefix = "WebCLIEngine.shutdown"
        log_api_enter(logger, log_prefix)
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
        log_api_exit(logger, log_prefix)

    #######################################################################
    # Thread management
    #######################################################################
    async def list_threads(self, user:User) -> List[Thread]:
        with Session(self.db_engine) as session:
            with session.begin():
                db_threads = list(session.query(DBThread)\
                    .filter(DBThread.user_id == user.id)\
                    .all())
                threads = [Thread.create(db_thread) for db_thread in db_threads]
        return threads
    
    async def create_thread(self, create_thread_request:CreateThreadRequest, user:User) -> Thread:
        with Session(self.db_engine) as session:
            with session.begin():
                db_thread = DBThread(
                    user_id = user.id,
                    created_at = get_utc_now(),
                    title = create_thread_request.title,
                    description = create_thread_request.description
                )
                session.add(db_thread)
            thread = Thread.create(db_thread)
        return thread

    async def get_thread(self, thread_id:int) -> Optional[Thread]:
        with Session(self.db_engine) as session:
            with session.begin():
                db_thread = session.get(DBThread, thread_id)
                db_thread_actions = session.scalars(
                    select(DBThreadAction)\
                        .join(DBThreadAction.action)\
                        .where(DBThreadAction.thread_id == thread_id)\
                        .order_by(DBThreadAction.display_order)
                )
            
            if db_thread is None:
                thread = None
            else:
                thread = Thread.create(db_thread, db_thread_actions=db_thread_actions)
        return thread

    async def patch_thread(self, thread_id:int, request_data:PatchThreadRequest) -> Optional[Thread]:
        with Session(self.db_engine) as session:
            with session.begin():
                db_thread:DBThread = session.get(DBThread, thread_id)
                if db_thread is None:
                    return None

                if request_data.title is not None:
                    db_thread.title = request_data.title
                if request_data.description is not None:
                    db_thread.description = request_data.description
                
                if request_data.title is not None or request_data.description is not None:
                    session.add(db_thread)
            thread = Thread.create(db_thread)
        return thread

    async def delete_thread(self, thread_id:int):
        with Session(self.db_engine) as session:
            with session.begin():
                # delete all related thread actions
                stmt = delete(DBThreadAction)\
                    .where(DBThreadAction.thread_id == thread_id)
                session.execute(stmt)

                # delete the thread
                stmt = delete(DBThread)\
                    .where(DBThread.id == thread_id)
                session.execute(stmt)

    async def remove_action_from_thread(self, thread_id:int, action_id:int) -> None:
        with Session(self.db_engine) as session:
            with session.begin():
                stmt = delete(DBThreadAction)\
                    .where(DBThreadAction.thread_id == thread_id)\
                    .where(DBThreadAction.action_id == action_id)
                session.execute(stmt)
        return None

    async def patch_action(self, action_id:int, request_data:PatchActionRequest) -> Optional[Action]:
        with Session(self.db_engine) as session:
            with session.begin():
                db_action:DBAction = session.get(DBAction, action_id)
                if db_action is None:
                    return None
                db_action.title = request_data.title
                session.add(db_action)
            action = Action.create(db_action)
        return action

    async def patch_thread_action(self, thread_id:int, action_id:int, request_data:PatchThreadActionRequest) -> Optional[ThreadAction]:
        with Session(self.db_engine) as session:
            with session.begin():
                db_thread_action = session.scalars(
                    select(DBThreadAction)\
                        .where(DBThreadAction.thread_id == thread_id)\
                        .where(DBThreadAction.action_id == action_id)
                ).one_or_none()
                if db_thread_action is None:
                    return None
                
                changes = 0
                if request_data.show_question is not None:
                    db_thread_action.show_question = request_data.show_question
                    changes += 1
                if request_data.show_answer is not None:
                    db_thread_action.show_answer = request_data.show_answer
                    changes += 1
                if changes > 0:
                    session.add(db_thread_action)
            return ThreadAction.create(db_thread_action)


    #######################################################################
    # Called by async function so they can submit a job to the thread pool
    #######################################################################
    async def _async_call(self, method:Any, *args, **kwargs) -> Any:
        v = AsyncCall(event_loop=self.event_loop)
        self.executor.submit(method, *args, async_call=v, **kwargs)
        # the method is responsible to finish the async call, optionally with return_value
        return await v.async_await_return()
    
    #######################################################################
    # Usually called by FastAPI async web handler directly
    #######################################################################
    async def async_start_action(self, request:CreateActionRequest, user:User, thread_id:int) -> Tuple[WebCLIEngineStatus, Optional[ThreadAction]]:
        log_prefix = "WebCLIEngine:async_start_action"
        log_api_enter(logger, log_prefix)
        status, action = await self._async_call(self.start_action, request, user, thread_id)
        log_api_exit(logger, log_prefix)
        return status, action

    async def async_update_action(self, action_id:int, progress:Any) -> WebCLIEngineStatus:
        log_prefix = "WebCLIEngine:async_update_action"
        log_api_enter(logger, log_prefix)
        logger.debug(f"{log_prefix}: action_id={action_id}")
        r = await self._async_call(self.update_action, action_id, progress)
        log_api_exit(logger, log_prefix)
        return r

    async def async_complete_action(self, action_id:int, response:Any) -> WebCLIEngineStatus:
        log_prefix = "WebCLIEngine:async_complete_action"
        log_api_enter(logger, log_prefix)
        logger.debug(f"{log_prefix}: action_id={action_id}")
        r = await self._async_call(self.complete_action, action_id, response)
        log_api_exit(logger, log_prefix)
        return r

    def _start_action_unsafe(
        self, 
        request:CreateActionRequest,
        user:User,
        thread_id:int,
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[WebCLIEngineStatus, Optional[ThreadAction]]:
        log_prefix = "WebCLIEngine.start_action_unsafe"
        #############################################################
        # Start an action
        #############################################################
        log_api_enter(logger, log_prefix)
        if self.require_shutdown:
            rs = WebCLIEngineStatus.SHUTDOWN_IN_PROGRESS
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            log_api_exit(logger, log_prefix)
            return rs, None
        
        found_action_handler = None
        found_action_handler_name = None
        for action_handler_name, action_handler in self.action_handlers.items():
            if action_handler.can_handle(request.request):
                found_action_handler = action_handler
                found_action_handler_name = action_handler_name
                logger.debug(f"{log_prefix}: found action handler, it is {found_action_handler}")
                break
        if found_action_handler is None:
            rs = WebCLIEngineStatus.NO_HANDLER
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            log_api_exit(logger, log_prefix)
            return rs, None
        
        # persist async action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    # try to get user configuration for the action handler
                    db_ahc = session.scalars(
                        select(DBActionHandlerConfiguration)\
                            .where(DBActionHandlerConfiguration.action_handler_name == found_action_handler_name)\
                            .where(DBActionHandlerConfiguration.user_id == user.id)
                    ).one_or_none()
                    if db_ahc is None:
                        action_handler_user_config = {}
                    else:
                        action_handler_user_config = db_ahc.configuration

                    # try to make sure the new action has the greatest display order within the thread
                    q = select(
                        func.max(DBThreadAction.display_order)
                    ).where(DBThreadAction.thread_id == thread_id)
                    old_max_display_order = session.scalars(q).one()
                    if old_max_display_order is None:
                        display_order = 1
                    else:
                        display_order = old_max_display_order + 1

                    db_action = DBAction(
                        handler_name = found_action_handler_name,
                        is_completed = False,
                        user_id = user.id,
                        created_at = get_utc_now(),
                        completed_at = None,
                        updated_at = None,
                        request = request.request,
                        title = request.title,
                        raw_text = request.raw_text,
                        response = None,
                        progress = None
                    )
                    session.add(db_action)
                    db_thread_action = DBThreadAction(
                        thread_id=thread_id,
                        action = db_action,
                        display_order = display_order,
                        show_question = False,
                        show_answer = True
                    )
                    session.add(db_thread_action)
                thread_action = ThreadAction.create(db_thread_action)
                logger.debug(f"{log_prefix}: action(id={thread_action.action.id}) is created")
        except SQLAlchemyError:
            logger.error(f"{log_prefix}: unable to update database for async action", exc_info=True)
            rs = WebCLIEngineStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            log_api_exit(logger, log_prefix)
            return rs, None

        with self.lock:
            # let handler to work in the thread pool
            logger.debug(f"{log_prefix}: invoking handler in thread pool, handler {found_action_handler.handle}")
            self.executor.submit(
                found_action_handler.handle, 
                thread_action.action.id, 
                request.request, 
                user, 
                action_handler_user_config
            )

            rs = WebCLIEngineStatus.OK
            if async_call is not None:
                async_call.finish(return_value=(rs, thread_action))
            
            log_api_exit(logger, log_prefix)
            return rs, thread_action

    def start_action(
        self, 
        request:CreateActionRequest, 
        user: User,
        thread_id:int,
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[WebCLIEngineStatus, Optional[ThreadAction]]:
        try:
            return self._start_action_unsafe(request, user, thread_id, async_call=async_call)
        except:
            logger.error("WebCLIEngine.start_async_action_unsafe: exception captured", exc_info=True)
            raise


    def _update_action_unsafe(
        self, 
        action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> WebCLIEngineStatus:
        #############################################################
        # Update an async action's progress
        #############################################################
        log_prefix = "WebCLIEngine:update_action_unsafe"
        log_api_enter(logger, log_prefix)
        logger.debug(f"{log_prefix}: action_id={action_id}")

        # persist action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action:DBAction = session.get(DBAction, action_id)
                    if db_action is None:
                        status = WebCLIEngineStatus.NOT_FOUND
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        log_api_exit(logger, log_prefix)
                        return status
                    
                    if db_action.is_completed:
                        status = WebCLIEngineStatus.ACTION_COMPLETED
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        log_api_exit(logger, log_prefix)
                        return status
                    
                    db_action.updated_at = get_utc_now()
                    db_action.progress = progress
                    session.add(db_action)
                action = Action.create(db_action)
        except SQLAlchemyError:
            logger.error(f"{log_prefix}: unable to update database for {action_to_str(action)}", exc_info=True)
            status = WebCLIEngineStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=status)
            log_api_exit(logger, log_prefix)
            return status

        logger.debug(f"{log_prefix}: {action_to_str(action)} is updated in database")

        status = WebCLIEngineStatus.OK
        if async_call is not None:
            async_call.finish(return_value=status)
        log_api_exit(logger, log_prefix)
        return status
    
    def update_action(
        self, action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> WebCLIEngineStatus:
        try:
            return self._update_action_unsafe(action_id, user, progress, async_call=async_call)
        except:
            logger.error("WebCLIEngine.update_action_unsafe: exception captured", exc_info=True)
            raise

    def _complete_action_unsafe(
        self, 
        action_id:int, 
        response:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> WebCLIEngineStatus:
        #############################################################
        # Complete an action's progress
        #############################################################
        log_prefix = "WebCLIEngine:complete_action_unsafe"
        log_api_enter(logger, log_prefix)
        logger.debug(f"{log_prefix}: action_id={action_id}")
        
        # persist action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action = session.get(DBAction, action_id)
                    if db_action is None:
                        status = WebCLIEngineStatus.NOT_FOUND
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        log_api_exit(logger, log_prefix)
                        return status

                    if db_action.is_completed:
                        status = WebCLIEngineStatus.ACTION_COMPLETED
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        log_api_exit(logger, log_prefix)
                        return status

                    db_action.is_completed = True
                    db_action.completed_at = get_utc_now()
                    db_action.response = response
                    session.add(db_action)
                action = Action.create(db_action)
        except SQLAlchemyError:
            logger.error(f"{log_prefix}: unable to update database for {action_to_str(action)}", exc_info=True)
            status = WebCLIEngineStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=status)
            log_api_exit(logger, log_prefix)
            return status

        logger.debug(f"{log_prefix}: {action_to_str(action)} is updated in database")

        status = WebCLIEngineStatus.OK
        if async_call is not None:
            async_call.finish(return_value=status)
        log_api_exit(logger, log_prefix)
        return status
        

    def complete_action(
        self, 
        action_id:int, 
        response:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> WebCLIEngineStatus:
        try:
            return self._complete_action_unsafe(action_id, response, async_call=async_call)
        except:
            logger.error("WebCLIEngine.complete_action_unsafe: exception captured", exc_info=True)
            raise

    
    ####################################################################################################
    # set action handler configuration for a client
    ####################################################################################################
    def set_action_handler_configuration(self, action_handler_name:str, user_id:int, configuration:Any) -> ActionHandlerConfiguration:
        with Session(self.db_engine) as session:
            with session.begin():
                db_ahc_list = list(session.query(DBActionHandlerConfiguration)\
                    .filter(DBActionHandlerConfiguration.action_handler_name == action_handler_name)\
                    .filter(DBActionHandlerConfiguration.user_id == user_id)\
                    .all())
                if len(db_ahc_list) == 0:
                    db_ahc = DBActionHandlerConfiguration(
                        action_handler_name = action_handler_name,
                        user_id = user_id,
                        created_at = get_utc_now(),
                        updated_at = None,
                        configuration = configuration
                    )
                else:
                    db_ahc = db_ahc_list[0]
                    db_ahc.updated_at = get_utc_now()
                    db_ahc.configuration = configuration
                session.add(db_ahc)
            return ActionHandlerConfiguration.create(db_ahc)

    ####################################################################################################
    # set action handler configuration for a client
    ####################################################################################################
    def get_action_handler_configuration(self, action_handler_name:str, user_id:int) -> Optional[ActionHandlerConfiguration]:
        with Session(self.db_engine) as session:
            db_ahc_list = list(session.query(DBActionHandlerConfiguration)\
                .filter(DBActionHandlerConfiguration.action_handler_name == action_handler_name)\
                .filter(DBActionHandlerConfiguration.user_id == user_id)\
                .all())
            if len(db_ahc_list) == 0:
                return None
            
            return ActionHandlerConfiguration.create(db_ahc_list[0])


    ####################################################################################################
    # set action handler configuration for a client
    ####################################################################################################
    async def get_action_handler_configurations(self, user_id:int) -> List[ActionHandlerConfiguration]:
        with Session(self.db_engine) as session:
            db_ahc_list = list(session.query(DBActionHandlerConfiguration)\
                .filter(DBActionHandlerConfiguration.user_id == user_id)\
                .all())
            
            return [ActionHandlerConfiguration.create(db_ahc) for db_ahc in db_ahc_list]


    ####################################################################################################
    # notify a web socket client an action is done
    ####################################################################################################
    def notify_websockt_client(self, client_id:str, action_id:int, response:BaseModel):
        asyncio.run_coroutine_threadsafe(
            self.wsc_manager.publish_notification(
                client_id, 
                action_id,
                response
            ),
            self.event_loop
        )
