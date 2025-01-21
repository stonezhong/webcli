import logging
logger = logging.getLogger(__name__)

from typing import Dict, Tuple, Any, List, Optional
from datetime import datetime, timezone
from asyncio import Event, get_event_loop, AbstractEventLoop, wait_for, TimeoutError
import enum
from concurrent.futures import ThreadPoolExecutor
import threading
import asyncio
from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from webcli2.db_models import DBAction, DBActionHandlerConfiguration
from webcli2.models import Action, ActionHandlerConfiguration
from webcli2.websocket import WebSocketConnectionManager

from abc import ABC, abstractmethod

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

class ActionHandler(ABC):
    webcli_engine: "WebCLIEngine" = None
    wsc_manager: WebSocketConnectionManager = None
    require_shutdown: Optional[bool] = None

    # can you handle this request?
    @abstractmethod
    def can_handle(self, request:Any) -> bool:
        pass # pragma: no cover

    def startup(self, webcli_engine:"WebCLIEngine"):
        assert self.require_shutdown is None
        assert self.webcli_engine is None

        self.require_shutdown = False
        self.webcli_engine = webcli_engine

    def shutdown(self):
        # assert self.require_shutdown == False
        # assert self.cli_handler is not None

        # self.cli_handler = None
        # self.require_shutdown = None
        pass

    @abstractmethod
    def handle(self, action_id:int, request:Any):
        # to complete the action, you can call
        # cli_handler.complete_action(None, action_id, ...)
        #
        # to update the action, you can call
        # cli_handler.update_action(None, action_id:int, ...):
        pass # pragma: no cover


class WebCLIEngine:
    db_engine: Engine                               # SQLAlchemy engine
    wsc_manager: WebSocketConnectionManager         # Web Socket Connection Manager
    executor: Optional[ThreadPoolExecutor]          # A thread pool
    event_loop: Optional[AbstractEventLoop]         # The current main loop
    lock: threading.Lock                            # a global lock
    require_shutdown: Optional[bool]                # True if shutdown has been requested
    action_handlers: List[ActionHandler]            # List of registered action handler

    def __init__(self, *, db_engine:Engine, wsc_manager:WebSocketConnectionManager, action_handlers:List[ActionHandler]):
        log_prefix = "WebCLIEngine.__init__"
        logger.debug(f"{log_prefix}: enter")
        self.db_engine = db_engine
        self.wsc_manager = wsc_manager
        self.executor = None
        self.event_loop = None
        self.lock = threading.Lock()
        self.require_shutdown = None
        self.action_handlers = action_handlers[:]
        logger.debug(f"{log_prefix}: exit")


    def startup(self):
        log_prefix = "WebCLIEngine.startup"
        # TODO: maybe I should limit the thread number
        logger.debug(f"{log_prefix}: enter")
        self.require_shutdown = False
        self.executor = ThreadPoolExecutor()

        self.event_loop = get_event_loop()
        logger.debug(f"{log_prefix}: event loop is {self.event_loop}")

        # register all action handler
        for action_handler in self.action_handlers:
            # TODO: if an action failed to startup, remove it since it may not handle
            #       request properly
            try:
                logger.debug(f"{log_prefix}: startup action handler {action_handler}")
                action_handler.startup(self)
            except Exception:
                # we will tolerate if action handler failed to startup
                logger.error(f"{log_prefix}: action handler startup exception", exc_info=True)

        logger.debug(f"{log_prefix}: exit")

    def shutdown(self):
        log_prefix = "WebCLIEngine.shutdown"
        logger.debug(f"{log_prefix}: enter")
        assert self.require_shutdown == False
        self.require_shutdown = True

        # shutdown all action handler
        for action_handler in reversed(self.action_handlers):
            try:
                logger.debug(f"{log_prefix}: shutdown action handler {action_handler}")
                action_handler.shutdown()
            except Exception:
                # we will tolerate if action handler failed to shutdown
                logger.error(f"{log_prefix}: action handler shutdown exception", exc_info=True)
        # TODO: what if some request are stuck, shall we hang on shutdown?
        self.executor.shutdown(wait=True)
        logger.debug(f"{log_prefix}: exit")

    #######################################################################
    # Called by async function so they can submit a job to the thread pool
    #######################################################################
    async def _async_call(self, method:Any, *args, **kwargs) -> Any:
        v = AsyncCall(event_loop=self.event_loop)
        self.executor.submit(method, *args, async_call=v, **kwargs)
        # the method is responsible to finish the async call, optionally with return_value
        return await v.async_await_return()
    
    async def async_start_action(self, request:Any) -> Tuple[WebCLIEngineStatus, Optional[Action]]:
        log_prefix = "WebCLIEngine:async_start_action"
        logger.debug(f"{log_prefix}: enter")
        status, action = await self._async_call(self.start_action, request)
        logger.debug(f"{log_prefix}: exit, status={status}, action={action_to_str(action)}")
        return status, action

    async def async_update_action(self, action_id:int, progress:Any) -> WebCLIEngineStatus:
        log_prefix = "WebCLIEngine:async_update_action"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        r = await self._async_call(self.update_action, action_id, progress)
        logger.debug(f"{log_prefix}: exit, status={r}")
        return r

    async def async_complete_action(self, action_id:int, response:Any) -> WebCLIEngineStatus:
        log_prefix = "WebCLIEngine:async_complete_action"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        r = await self._async_call(self.complete_action, action_id, response)
        logger.debug(f"{log_prefix}: exit, status={r}")
        return r

    def _start_action_unsafe(
        self, 
        request:Any,
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[WebCLIEngineStatus, Optional[Action]]:
        log_prefix = "WebCLIEngine.start_action_unsafe"
        #############################################################
        # Start an action
        #############################################################
        logger.debug(f"{log_prefix}: enter")
        if self.require_shutdown:
            rs = WebCLIEngineStatus.SHUTDOWN_IN_PROGRESS
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            logger.debug(f"{log_prefix}: exit, status={rs}, action=None")
            return rs, None
        
        found_action_handler = None
        for action_handler in self.action_handlers:
            if action_handler.can_handle(request):
                found_action_handler = action_handler
                logger.debug(f"{log_prefix}: found action handler, it is {found_action_handler}")
                break
        if found_action_handler is None:
            rs = WebCLIEngineStatus.NO_HANDLER
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            logger.debug(f"{log_prefix}: exit, status={rs}, action=None")
            return rs, None

        # persist async action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action = DBAction(
                        is_completed = False,
                        created_at = get_utc_now(),
                        completed_at = None,
                        updated_at = None,
                        request = request,
                        response = None,
                        progress = None
                    )
                    session.add(db_action)
                action = Action.create(db_action)
        except SQLAlchemyError:
            logger.error(f"{log_prefix}: unable to update database for async action", exc_info=True)
            rs = WebCLIEngineStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            logger.debug(f"{log_prefix}: exit, status=rs, action=None")
            return rs, None

        with self.lock:
            # let handler to work in the thread pool
            logger.debug(f"{log_prefix}: invoking handle in thread pool, handler {found_action_handler.handle}")
            self.executor.submit(found_action_handler.handle, action.id, request)

            rs = WebCLIEngineStatus.OK
            if async_call is not None:
                async_call.finish(return_value=(rs, action))
            
            logger.debug(f"{log_prefix}: exit, status={rs}, action={action_to_str(action)})")
            return rs, action

    def start_action(
        self, 
        request:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[WebCLIEngineStatus, Optional[Action]]:
        try:
            return self._start_action_unsafe(request, async_call=async_call)
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
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        action_info = None

        # persist action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action:DBAction = session.get(DBAction, action_id)
                    if db_action is None:
                        status = WebCLIEngineStatus.NOT_FOUND
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        logger.debug(f"{log_prefix}: exit, status={status}")
                        return status
                    
                    if db_action.is_completed:
                        status = WebCLIEngineStatus.ACTION_COMPLETED
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        logger.debug(f"{log_prefix}: exit, status={status}")
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
            logger.debug("{log_prefix}: exit, status={status}")
            return status

        logger.debug(f"{log_prefix}: {action_to_str(action)} is updated in database")

        status = WebCLIEngineStatus.OK
        if async_call is not None:
            async_call.finish(return_value=status)
        logger.debug(f"{log_prefix}: exit, status={status}")
        return status
    
    def update_action(
        self, action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> WebCLIEngineStatus:
        try:
            return self._update_action_unsafe(action_id, progress, async_call=async_call)
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
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        action_info = None
        
        # persist action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action = session.get(DBAction, action_id)
                    if db_action is None:
                        status = WebCLIEngineStatus.NOT_FOUND
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        logger.debug(f"{log_prefix}: exit, status={status}")
                        return status

                    if db_action.is_completed:
                        status = WebCLIEngineStatus.ACTION_COMPLETED
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        logger.debug(f"{log_prefix}: exit, status={status}")
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
            logger.debug(f"WebCLIEngine.complete_action_unsafe: exit, status={status}")
            return status

        logger.debug(f"{log_prefix}: {action_to_str(action)} is updated in database")

        status = WebCLIEngineStatus.OK
        if async_call is not None:
            async_call.finish(return_value=status)
        logger.debug(f"{log_prefix}: exit, status={status}")
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
    def set_action_handler_configuration(self, action_handler_name:str, client_id:str, configuration:Any) -> ActionHandlerConfiguration:
        with Session(self.db_engine) as session:
            with session.begin():
                db_ahc_list = list(session.query(DBActionHandlerConfiguration)\
                    .filter(DBActionHandlerConfiguration.action_handler_name == action_handler_name)\
                    .filter(DBActionHandlerConfiguration.client_id == client_id)\
                    .all())
                if len(db_ahc_list) == 0:
                    db_ahc = DBActionHandlerConfiguration(
                        action_handler_name = action_handler_name,
                        client_id = client_id,
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
    def get_action_handler_configuration(self, action_handler_name:str, client_id:str) -> Optional[ActionHandlerConfiguration]:
        with Session(self.db_engine) as session:
            db_ahc_list = list(session.query(DBActionHandlerConfiguration)\
                .filter(DBActionHandlerConfiguration.action_handler_name == action_handler_name)\
                .filter(DBActionHandlerConfiguration.client_id == client_id)\
                .all())
            if len(db_ahc_list) == 0:
                return None
            
            return ActionHandlerConfiguration.create(db_ahc_list[0])


    ####################################################################################################
    # set action handler configuration for a client
    ####################################################################################################
    async def get_action_handler_configurations(self, client_id:str) -> List[ActionHandlerConfiguration]:
        with Session(self.db_engine) as session:
            db_ahc_list = list(session.query(DBActionHandlerConfiguration)\
                .filter(DBActionHandlerConfiguration.client_id == client_id)\
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
