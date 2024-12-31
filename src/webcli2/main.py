import logging
logger = logging.getLogger("webcli")

from typing import Dict, Tuple, Any, List, Optional
from datetime import datetime, timezone
from asyncio import Event, get_event_loop, AbstractEventLoop, wait_for, TimeoutError
import enum
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from webcli2.db_models import DBAction
from webcli2.models import Action

from abc import ABC, abstractmethod

#############################################################
# async method name start with async_
#############################################################

#############################################################
# Get the current UTC time
#############################################################
def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# this is only for logging
def action_to_str(action:Optional[Action]) -> str:
    return "None" if action is None else f"Action(id={action.id})"

# this is only for logging
def monitoring_client_to_str(monitoring_client:Optional["ActionMonitoringClient"]) -> str:
    return "None" if monitoring_client is None else f"ActionMonitoringClient(id={monitoring_client.id})"

class ActionHandler(ABC):
    cli_handler: "CLIHandler" = None
    require_shutdown: Optional[bool] = None

    # can you handle this request?
    @abstractmethod
    def can_handle(self, request:Any) -> bool:
        pass # pragma: no cover

    def startup(self, cli_handler: "CLIHandler"):
        assert self.require_shutdown is None
        assert self.cli_handler is None

        self.require_shutdown = False
        self.cli_handler = cli_handler

    @abstractmethod
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

# Status code for CLIHandler API calls
class CLIHandlerStatus(enum.Enum):
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

#############################################################
# Tracking the update of an Action of a given client
#############################################################
class ActionMonitoringClient:
    id: uuid.UUID # an unique ID
    action: Action
    event: Event
    pending_removal: bool

    def __init__(self, action:Action):
        self.id = uuid.uuid4()
        self.event = Event()
        self.action = action
        self.pending_removal = False

    async def async_wait_for_update(self, timeout:float) -> Optional[Action]:
        #############################################################
        # wait for the Action to be updated or timed out
        # each ActionMonitoringClient can only be waited once
        #############################################################
        try:
            await wait_for(self.event.wait(), timeout=timeout)
            return self.action
        except TimeoutError:
            self.pending_removal = True
            return None

#############################################################
# Tracking the update of an Action
#############################################################
class ActionInfo:
    action: Action
    monitoring_client_dict: Dict[uuid.UUID, ActionMonitoringClient]
    lock: threading.Lock

    def __init__(self, action:Action):
        self.action = action
        self.monitoring_client_dict = {}
        self.lock = threading.Lock()
    
    def create_client(self) -> ActionMonitoringClient:
        moniroing_client = ActionMonitoringClient(self.action)
        self.monitoring_client_dict[moniroing_client.id] = moniroing_client
        return moniroing_client

class CLIHandler:
    debug: bool
    db_engine: Engine
    executor: Optional[ThreadPoolExecutor]
    scavenger_thread: Optional[threading.Thread]
    event_loop: Optional[AbstractEventLoop]
    lock: threading.Lock
    action_info_dict: Dict[int, ActionInfo] # key is action ID
    require_shutdown: Optional[bool]
    action_handlers: List[ActionHandler]
    run_scavenger: bool

    def __init__(self, *, db_engine:Engine, debug:bool=False, action_handlers:List[ActionHandler], run_scavenger=False):
        self.debug = debug
        self.db_engine = db_engine
        self.executor = None
        self.scavenger_thread = None
        self.event_loop = None
        self.lock = threading.Lock()
        self.action_info_dict = {}
        self.require_shutdown = None
        self.action_handlers = action_handlers[:]
        self.run_scavenger = run_scavenger

    def scavenger(self):
        logger.debug("scavenger: enter")
        while not self.require_shutdown:
            logger.debug("scavenger: working")
            # TODO: adding real actions here, make sure to catch exception to prevent scavenger from being stopped
            time.sleep(5)
        logger.debug("scavenger: exit")

    def startup(self):
        log_prefix = "CLIHandler.startup"
        # TODO: maybe I should limit the thread number
        logger.debug(f"{log_prefix}: enter")
        self.require_shutdown = False
        self.executor = ThreadPoolExecutor()

        # If you want scavenger to run in background, enable lines below
        if self.run_scavenger:
            self.scavenger_thread = threading.Thread(target=self.scavenger, daemon=True)
            self.scavenger_thread.start()

        self.event_loop = get_event_loop()

        # register all action handler
        for action_handler in self.action_handlers:
            try:
                logger.debug(f"CLIHandler.startup: startup action handler {action_handler}")
                action_handler.startup(self)
            except Exception:
                # we will tolerate if action handler failed to startup
                logger.error(f"CLIHandler.startup: action handler startup exception", exc_info=True)
        # load pending Action that is stored in database
        with Session(self.db_engine) as session:
            for db_action in session.query(DBAction).filter(DBAction.is_completed == False).all():
                self.action_info_dict[db_action.id] = ActionInfo(Action.create(db_action))

        logger.debug(f"{log_prefix}: {len(self.action_info_dict)} pending actions loaded from db")
        logger.debug(f"{log_prefix}: enter")

    def shutdown(self):
        # TODO: what if some request are stuck, shall we hang on shutdown?
        logger.debug("CLIHandler.shutdown: enter")
        assert self.require_shutdown == False
        self.require_shutdown = True

        # shutdown all action handler
        for action_handler in reversed(self.action_handlers):
            try:
                logger.debug(f"CLIHandler.shutdown: shutdown action handler {action_handler}")
                action_handler.shutdown()
            except Exception:
                # we will tolerate if action handler failed to shutdown
                logger.error(f"CLIHandler.shutdown: action handler shutdown exception", exc_info=True)
        if self.scavenger_thread is not None:
            self.scavenger_thread.join()
        self.executor.shutdown(wait=True)
        logger.debug("CLIHandler.shutdown: exit")

    #######################################################################
    # Called by async function so they can submit a job to the thread pool
    #######################################################################
    async def _async_call(self, method:Any, *args, **kwargs) -> Any:
        v = AsyncCall(event_loop=self.event_loop)
        self.executor.submit(method, *args, async_call=v, **kwargs)
        # the method is responsible to finish the async call, optionally with return_value
        return await v.async_await_return()
    
    async def async_start_action(self, request:Any) -> Tuple[CLIHandlerStatus, Optional[Action]]:
        log_prefix = "CLIHandler:async_start_action"
        logger.debug(f"{log_prefix}: enter")
        status, action = await self._async_call(self.start_action, request)
        logger.debug(f"{log_prefix}: exit, status={status}, action={action_to_str(action)}")
        return status, action

    async def async_update_action(self, action_id:int, progress:Any) -> CLIHandlerStatus:
        log_prefix = "CLIHandler:async_update_action"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        r = await self._async_call(self.update_action, action_id, progress)
        logger.debug(f"{log_prefix}: exit, status={r}")
        return r

    async def async_complete_action(self, action_id:int, response:Any) -> CLIHandlerStatus:
        log_prefix = "CLIHandler:async_complete_action"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        r = await self._async_call(self.complete_action, action_id, response)
        logger.debug(f"{log_prefix}: exit, status={r}")
        return r

    async def async_register_monitor_action(self, action_id:int) -> Tuple[CLIHandlerStatus, Optional[ActionMonitoringClient]]:
        log_prefix = "CLIHandler:async_register_monitor_action"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        status, monitoring_client = await self._async_call(self.register_monitoring_client, action_id)
        logger.debug(f"{log_prefix}: exit, status={status}, monitoring_client={monitoring_client_to_str(monitoring_client)}")
        return status, monitoring_client
    
    async def async_remove_monitoring_client(self, action_id:int, moniroting_client_id: uuid.UUID):
        log_prefix = "CLIHandler:async_remove_monitoring_client"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}, moniroting_client_id={moniroting_client_id}")
        r = await self._async_call(self.remove_monitoring_client, action_id, moniroting_client_id)
        logger.debug(f"{log_prefix}: exit")
        return r

    async def async_wait_for_action_update(self, action_id:int, timeout:float) -> Tuple[CLIHandlerStatus, Optional[Action]]:
        log_prefix = "CLIHandler.async_wait_for_action_update"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}, timeout={timeout}")
        
        status, monitoring_client = await self.async_register_monitor_action(action_id)
        if status in (CLIHandlerStatus.NOT_FOUND, CLIHandlerStatus.ACTION_COMPLETED):
            logger.debug(f"{log_prefix}: exit, status={status}, action=None")
            return status, None

        assert status == CLIHandlerStatus.OK
        action = await monitoring_client.async_wait_for_update(timeout)

        try:
            status = CLIHandlerStatus.TIMEDOUT if action is None else CLIHandlerStatus.OK
            logger.debug(f"{log_prefix}: exit, status={status}, action={action_to_str(action)}")
            return status, action
        finally:
            await self.async_remove_monitoring_client(monitoring_client.action.id, monitoring_client.id)


    def start_action_unsafe(
        self, 
        request:Any,
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[CLIHandlerStatus, Optional[Action]]:
        log_prefix = "CLIHandler.start_action_unsafe"
        #############################################################
        # Start an action
        #############################################################
        logger.debug("{log_prefix}: enter")
        if self.require_shutdown:
            rs = CLIHandlerStatus.SHUTDOWN_IN_PROGRESS
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
            rs = CLIHandlerStatus.NO_HANDLER
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
            rs = CLIHandlerStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=(rs, None))
            logger.debug(f"{log_prefix}: exit, status=rs, action=None")
            return rs, None

        with self.lock:
            # for new action, it should not be in database
            assert action.id not in self.action_info_dict
            self.action_info_dict[action.id] = ActionInfo(action)

            # let handler to work in the thread pool
            logger.debug(f"{log_prefix}: invoking handle in thread pool, handler {found_action_handler.handle}")
            self.executor.submit(found_action_handler.handle, action.id, request)

            rs = CLIHandlerStatus.OK
            if async_call is not None:
                async_call.finish(return_value=(rs, action))
            
            logger.debug(f"{log_prefix}: exit, status={rs}, action={action_to_str(action)})")
            return rs, action

    def start_action(
        self, 
        request:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[CLIHandlerStatus, Optional[Action]]:
        if self.debug:
            try:
                return self.start_action_unsafe(request, async_call=async_call)
            except:
                logger.error("CLIHandler.start_async_action_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.start_action_unsafe(request, async_call=async_call)


    def update_action_unsafe(
        self, 
        action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> CLIHandlerStatus:
        #############################################################
        # Update an async action's progress
        #############################################################
        log_prefix = "CLIHandler:update_action_unsafe"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        action_info = None

        # persist action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action:DBAction = session.get(DBAction, action_id)
                    if db_action is None:
                        status = CLIHandlerStatus.NOT_FOUND
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        logger.debug(f"{log_prefix}: exit, status={status}")
                        return status
                    
                    if db_action.is_completed:
                        status = CLIHandlerStatus.ACTION_COMPLETED
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
            status = CLIHandlerStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=status)
            logger.debug("{log_prefix}: exit, status={status}")
            return status

        logger.debug(f"{log_prefix}: {action_to_str(action)} is updated in database")

        try:
            assert not self.lock.locked()
            self.lock.acquire()   # this is an expensive global lock
            action_info = self.action_info_dict[action_id]

            assert not action_info.lock.locked()
            action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            # handler lock: released
            # action_info: locked
            action_info.action.progress = progress
            action_info.action.updated_at = action.updated_at
            for _, client in action_info.monitoring_client_dict.items():
                if client.pending_removal:
                    logger.debug(f"{log_prefix}: skip set event for {monitoring_client_to_str(client)} due to pending removal mode")
                else:
                    logger.debug(f"{log_prefix}: set event for {monitoring_client_to_str(client)}")
                    client.pending_removal = True
                    self.event_loop.call_soon_threadsafe(client.event.set)
            
            status = CLIHandlerStatus.OK
            if async_call is not None:
                async_call.finish(return_value=status)
            logger.debug(f"{log_prefix}: exit, status={status}")
            return status
        finally:
            if self.lock.locked():
                self.lock.release()
            if action_info is not None and action_info.lock.locked():
                action_info.lock.release()
    
    def update_action(
        self, action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> CLIHandlerStatus:
        if self.debug:
            try:
                return self.update_action_unsafe(action_id, progress, async_call=async_call)
            except:
                logger.error("CLIHandler.update_action_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.update_action_unsafe(action_id, progress, async_call=async_call)


    def complete_action_unsafe(
        self, 
        action_id:int, 
        response:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> CLIHandlerStatus:
        #############################################################
        # Complete an action's progress
        #############################################################
        log_prefix = "CLIHandler:complete_action_unsafe"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        action_info = None
        
        # persist action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_action = session.get(DBAction, action_id)
                    if db_action is None:
                        status = CLIHandlerStatus.NOT_FOUND
                        if async_call is not None:
                            async_call.finish(return_value=status)
                        logger.debug(f"{log_prefix}: exit, status={status}")
                        return status

                    if db_action.is_completed:
                        status = CLIHandlerStatus.ACTION_COMPLETED
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
            status = CLIHandlerStatus.DB_FAILED
            if async_call is not None:
                async_call.finish(return_value=status)
            logger.debug(f"CLIHandler.complete_action_unsafe: exit, status={status}")
            return status

        logger.debug(f"{log_prefix}: {action_to_str(action)} is updated in database")

        try:
            assert not self.lock.locked()
            self.lock.acquire()   # this is an expensive global lock
            action_info = self.action_info_dict[action_id]

            assert not action_info.lock.locked()
            action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            # handler lock: released
            # action_info: locked
            action_info.action.is_completed = True
            action_info.action.completed_at = action.completed_at
            action_info.action.response = response
            for _, client in action_info.monitoring_client_dict.items():
                if client.pending_removal:
                    logger.debug(f"{log_prefix}: skip set event for {monitoring_client_to_str(client)} due to pending removal mode")
                else:
                    logger.debug(f"{log_prefix}: set event for {monitoring_client_to_str(client)}")
                    client.pending_removal = True
                    self.event_loop.call_soon_threadsafe(client.event.set)

            status = CLIHandlerStatus.OK
            if async_call is not None:
                async_call.finish(return_value=status)
            logger.debug(f"{log_prefix}: exit, status={status}")
            return status
        finally:
            if self.lock.locked():
                self.lock.release()
            if action_info is not None and action_info.lock.locked():
                action_info.lock.release()
        

    def complete_action(
        self, 
        action_id:int, 
        response:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> CLIHandlerStatus:
        if self.debug:
            try:
                return self.complete_action_unsafe(action_id, response, async_call=async_call)
            except:
                logger.error("CLIHandler.complete_action_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.complete_action_unsafe(action_id, response, async_call=async_call)

    def remove_monitoring_client_unsafe(
        self, 
        action_id:int, 
        moniroting_client_id: uuid.UUID, 
        async_call:Optional[AsyncCall]=None
    ) -> CLIHandlerStatus:
        #############################################################
        # Remove a monitoring client that is no longer needed
        #############################################################
        log_prefix = "CLIHandler.remove_monitoring_client_unsafe"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}, moniroting_client_id={moniroting_client_id}")
        action_info = None
        
        try:
            assert not self.lock.locked()
            self.lock.acquire()
            action_info = self.action_info_dict.get(action_id)

            if action_info is None:
                status = CLIHandlerStatus.NOT_FOUND
                logger.warning(f"{log_prefix}: Action(id={action_id}) is not found!")
                async_call.finish(return_value=status)
                logger.debug(f"{log_prefix}: exit, status={status}")
                return status

            assert not action_info.lock.locked()
            action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            monitoring_client = action_info.monitoring_client_dict.pop(moniroting_client_id, None)
            if monitoring_client is None:
                logger.warning(f"{log_prefix}: Action(id={action_id}) does not have ActionMonitoringClient(id={moniroting_client_id})")
                status = CLIHandlerStatus.NOT_FOUND
                async_call.finish(return_value=status)
                logger.debug(f"{log_prefix}: exit, status={status}")
                return status
            
            assert monitoring_client.action.id == action_id
            status = CLIHandlerStatus.OK
            async_call.finish(return_value=status)
            logger.debug(f"{log_prefix}: exit, status={status}")
            return status
        finally:
            if self.lock.locked():
                self.lock.release()
            if action_info is not None and action_info.lock.locked():
                action_info.lock.release()

    def remove_monitoring_client(
        self, 
        action_id:int, 
        moniroting_client_id: uuid.UUID, 
        async_call:Optional[AsyncCall]=None
    ) -> CLIHandlerStatus:
        if self.debug:
            try:
                return self.remove_monitoring_client_unsafe(action_id, moniroting_client_id, async_call=async_call)
            except:
                logger.error("CLIHandler.remove_monitoring_client_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.remove_monitoring_client_unsafe(action_id, moniroting_client_id, async_call=async_call)


    def register_monitoring_client_unsafe(
        self, 
        action_id:int, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[CLIHandlerStatus, ActionMonitoringClient]:
        #############################################################
        # Register a client, so the client can monitor if the async action is
        # completed or any updates
        #############################################################
        log_prefix = "CLIHandler.register_monitoring_client_unsafe"
        logger.debug(f"{log_prefix}: enter, action_id={action_id}")
        action_info = None

        try:
            assert not self.lock.locked()
            self.lock.acquire()   # this is an expensive global lock
            action_info = self.action_info_dict.get(action_id)
            if action_info is None:
                status = CLIHandlerStatus.NOT_FOUND
                async_call.finish(return_value=(status, None))
                logger.debug(f"{log_prefix}: exit, status={status}, monitoring_client=None")
                return status, None

            assert not action_info.lock.locked()
            action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            # handler lock: released
            # action_info: locked
            if action_info.action.is_completed:
                status = CLIHandlerStatus.ACTION_COMPLETED
                async_call.finish(return_value=(status, None))
                logger.debug(f"{log_prefix}: exit, status={status}, monitoring_client=None")
                return status, None
            
            status = CLIHandlerStatus.OK
            monitoring_client = action_info.create_client()
            async_call.finish(return_value=(status, monitoring_client))
            logger.debug(f"{log_prefix}: exit, status={status}, monitoring_client={monitoring_client_to_str(monitoring_client)}")
            return CLIHandlerStatus.OK, monitoring_client
        finally:
            if self.lock.locked():
                self.lock.release()
            if action_info is not None and action_info.lock.locked():
                action_info.lock.release()

    def register_monitoring_client(
        self, 
        action_id:int, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[CLIHandlerStatus, ActionMonitoringClient]:
        if self.debug:
            try:
                return self.register_monitoring_client_unsafe(action_id, async_call=async_call)
            except:
                logger.error("CLIHandler.register_monitoring_client_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.register_monitoring_client_unsafe(action_id, async_call=async_call)

