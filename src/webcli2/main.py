import logging
logger = logging.getLogger("webcli")

from typing import Dict, Tuple, Any, List, Optional
from datetime import datetime, timezone
from asyncio import Event, get_event_loop, AbstractEventLoop, wait_for, get_running_loop
import asyncio
import enum
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from webcli2.db_models import DBAsyncAction
from webcli2.models import AsyncAction

from abc import ABC, abstractmethod

#############################################################
# async method name start with async_
#############################################################

#############################################################
# Get the current UTC time
#############################################################
def get_utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def async_action_to_str(async_action:Optional[AsyncAction]) -> str:
    return "None" if async_action is None else f"AsyncAction(id={async_action.id})"

def monitoring_client_to_str(monitoring_client:Optional["AsyncActionMonitoringClient"]) -> str:
    return "None" if monitoring_client is None else f"AsyncActionMonitoringClient(id={monitoring_client.id})"

class AsyncActionHandler(ABC):
    # can you handle this request?
    @abstractmethod
    def can_handle(self, request:Any) -> bool:
        pass # pragma: no cover

    @abstractmethod
    def handle(self, action_id:int, request:Any, cli_handler: "CLIHandler"):
        # to complete the action, you can call
        # cli_handler.complete_async_action(None, action_id, ...)
        #
        # to update the action, you can call
        # cli_handler.update_progress_async_action(None, action_id:int, ...):
        pass # pragma: no cover

class AsyncActionOpStatus(enum.Enum):
    OK = 0
    DB_FAILED = 1               # database failure
    NOT_FOUND = 2               # you cannot update, monior, complete an action since the action does not exist
    ACTION_COMPLETED = 3        # you cannot update an action since the AsyncActionInfoaction has been completed
    TIMEDOUT = 4
    SHUTDOWN_IN_PROGRESS = 5    # we are shutting down
    NO_HANDLER = 6              # we cannot find a handler to handle this action

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
# Tracking the update of an AsyncAction of a given client
#############################################################
class AsyncActionMonitoringClient:
    id: uuid.UUID # an unique ID
    async_action: AsyncAction
    event: Event
    pending_removal: bool

    def __init__(self, async_action:AsyncAction):
        self.id = uuid.uuid4()
        self.event = Event()
        self.async_action = async_action
        self.pending_removal = False

    async def async_wait_for_update(self, timeout:float) -> Optional[AsyncAction]:
        #############################################################
        # wait for the AsyncAction to be updated or timed out
        # each AsyncActionMonitoringClient can only be waited once
        #############################################################
        ret = None
        try:
            await asyncio.wait_for(self.event.wait(), timeout=timeout)
            ret = self.async_action
        except asyncio.TimeoutError:
            self.pending_removal = True
            ret = None
        return ret

#############################################################
# Tracking the update of an AsyncAction
#############################################################
class AsyncActionInfo:
    async_action: AsyncAction
    monitoring_client_dict: Dict[uuid.UUID, AsyncActionMonitoringClient]
    lock: threading.Lock

    def __init__(self, async_action:AsyncAction):
        self.async_action = async_action
        self.monitoring_client_dict = {}
        self.lock = threading.Lock()
    
    def create_client_unsafe(self) -> AsyncActionMonitoringClient:
        moniroing_client = AsyncActionMonitoringClient(self.async_action)
        self.monitoring_client_dict[moniroing_client.id] = moniroing_client
        return moniroing_client

class CLIHandler:
    debug: bool
    db_engine: Engine
    executor: Optional[ThreadPoolExecutor]
    scavenger_thread: Optional[threading.Thread]
    event_loop: Optional[AbstractEventLoop]
    lock: threading.Lock
    async_action_info_dict: Dict[int, AsyncActionInfo] # key is action ID, value is AsyncActionInfo
    require_shutdown: Optional[bool]
    action_handlers: List[AsyncActionHandler]
    run_scavenger: bool

    def __init__(self, *, db_engine:Engine, debug:bool=False, action_handlers:List[AsyncActionHandler], run_scavenger=False):
        self.debug = debug
        self.db_engine = db_engine
        self.executor = None
        self.scavenger_thread = None
        self.event_loop = None
        self.lock = threading.Lock()
        self.async_action_info_dict = {}
        self.require_shutdown = None
        self.action_handlers = action_handlers
        self.run_scavenger = run_scavenger

    def scavenger(self):
        logger.debug("scavenger: enter")
        while not self.require_shutdown:
            logger.debug("scavenger: working")
            # TODO: adding real actions here, make sure to catch exception to prevent scavenger from being stopped
            time.sleep(5)
        logger.debug("scavenger: exit")

    def startup(self):
        # TODO: maybe I should limit the thread number
        logger.debug("CLIHandler.startup: enter")
        self.require_shutdown = False
        self.executor = ThreadPoolExecutor()

        # If you want scavenger to run in background, enable lines below
        if self.run_scavenger:
            self.scavenger_thread = threading.Thread(target=self.scavenger, daemon=True)
            self.scavenger_thread.start()
        self.event_loop = get_event_loop()

        # load pending AsyncAction that is stored in database
        with Session(self.db_engine) as session:
            for db_async_action in session.query(DBAsyncAction).filter(DBAsyncAction.is_completed == False).all():
                self.async_action_info_dict[db_async_action.id] = AsyncActionInfo(AsyncAction.create(db_async_action))

        logger.debug(f"CLIHandler.startup: {len(self.async_action_info_dict)} pending actions loaded from db")
        logger.debug("CLIHandler.startup: exit")

    def shutdown(self):
        # TODO: what if some request are stuck, shall we hang on shutdown?
        logger.debug("CLIHandler.shutdown: enter")
        self.require_shutdown = True
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
    
    async def async_start_async_action(self, request:Any) -> Tuple[AsyncActionOpStatus, Optional[AsyncAction]]:
        logger.debug("CLIHandler:async_start_async_action: enter")
        async_action_op_status, async_action = await self._async_call(self.start_async_action, request)
        logger.debug(f"CLIHandler:async_start_async_action: exit, status={async_action_op_status}, async_action={async_action_to_str(async_action)}")
        return async_action_op_status, async_action

    async def async_update_progress_async_action(self, action_id:int, progress:Any) -> AsyncActionOpStatus:
        logger.debug(f"CLIHandler:async_update_progress_async_action: enter, action_id={action_id}")
        r = await self._async_call(self.update_progress_async_action, action_id, progress)
        logger.debug(f"CLIHandler:async_update_progress_async_action: exit, status={r}")
        return r

    async def async_complete_async_action(self, action_id:int, response:Any) -> AsyncActionOpStatus:
        logger.debug(f"CLIHandler:async_complete_async_action: enter, action_id={action_id}")
        r = await self._async_call(self.complete_async_action, action_id, response)
        logger.debug(f"CLIHandler:async_complete_async_action: exit, status={r}")
        return r

    async def async_register_monitor_async_action(self, action_id:int) -> Tuple[AsyncActionOpStatus, Optional[AsyncActionMonitoringClient]]:
        logger.debug(f"CLIHandler:async_register_monitor_async_action: enter, action_id={action_id}")
        async_action_op_status, monitoring_client = await self._async_call(self.register_monitor_async_action, action_id)
        logger.debug(f"CLIHandler:async_register_monitor_async_action: exit, status={async_action_op_status}, monitoring_client={monitoring_client_to_str(monitoring_client)}")
        return async_action_op_status, monitoring_client
    
    async def async_remove_monitoring_client(self, action_id:int, moniroting_client_id: uuid.UUID):
        logger.debug(f"CLIHandler:async_remove_monitoring_client: enter, action_id={action_id}, moniroting_client_id={moniroting_client_id}")
        r = await self._async_call(self.remove_monitoring_client, action_id, moniroting_client_id)
        logger.debug("CLIHandler:async_remove_monitoring_client: exit")
        return r

    async def async_wait_for_update_async_action(self, action_id:int, timeout:float) -> Tuple[AsyncActionOpStatus, Optional[AsyncAction]]:
        logger.debug(f"CLIHandler:async_wait_for_update_async_action: enter, action_id={action_id}, timeout={timeout}")
        
        async_action_op_status, monitoring_client = await self.async_register_monitor_async_action(action_id)
        if async_action_op_status == AsyncActionOpStatus.NOT_FOUND:
            logger.debug(f"CLIHandler:async_wait_for_update_async_action: async action with id of {action_id} is not found")
            logger.debug(f"CLIHandler:async_wait_for_update_async_action: exit, status={async_action_op_status}, async_action=None")
            return async_action_op_status, None
        
        if async_action_op_status == AsyncActionOpStatus.ACTION_COMPLETED:
            logger.debug(f"CLIHandler:async_wait_for_update_async_action: async action with id of {action_id} is already completed")
            logger.debug(f"CLIHandler:async_wait_for_update_async_action: exit, status={async_action_op_status}, async_action=None")
            return async_action_op_status, None

        assert async_action_op_status == AsyncActionOpStatus.OK

        async_action = await monitoring_client.async_wait_for_update(timeout)

        try:
            if async_action is None:
                r = (AsyncActionOpStatus.TIMEDOUT, None)
                logger.debug(f"CLIHandler:async_wait_for_update_async_action: exit, status={AsyncActionOpStatus.TIMEDOUT}, async_action=None")
            else:
                r = (AsyncActionOpStatus.OK, async_action)
                logger.debug(f"CLIHandler:async_wait_for_update_async_action: exit, status={AsyncActionOpStatus.OK}, async_action={async_action_to_str(async_action)}")
            return r
        finally:
            await self.async_remove_monitoring_client(monitoring_client.async_action.id, monitoring_client.id)


    def start_async_action_unsafe(
        self, 
        request:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[AsyncActionOpStatus, Optional[AsyncAction]]:
        #############################################################
        # Start an async action
        #############################################################
        logger.debug("CLIHandler.start_async_action_unsafe: enter")
        if self.require_shutdown:
            if async_call is not None:
                async_call.finish(return_value=(AsyncActionOpStatus.SHUTDOWN_IN_PROGRESS, None))
            logger.debug(f"CLIHandler.start_async_action_unsafe: exit, status={AsyncActionOpStatus.SHUTDOWN_IN_PROGRESS}, async_action=None")
            return AsyncActionOpStatus.SHUTDOWN_IN_PROGRESS, None
        
        found_action_handler = None
        for action_handler in self.action_handlers:
            if action_handler.can_handle(request):
                found_action_handler = action_handler
                break
        if found_action_handler is None:
            if async_call is not None:
                async_call.finish(return_value=(AsyncActionOpStatus.NO_HANDLER, None))
            logger.debug(f"CLIHandler.start_async_action_unsafe: exit, status={AsyncActionOpStatus.NO_HANDLER}, async_action=None")
            return AsyncActionOpStatus.NO_HANDLER, None

        # persist async action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_async_action = DBAsyncAction(
                        is_completed = False,
                        created_at = get_utc_now(),
                        completed_at = None,
                        updated_at = None,
                        request = request,
                        response = None,
                        progress = None
                    )
                    session.add(db_async_action)

                async_action = AsyncAction.create(db_async_action)
        except SQLAlchemyError:
            logger.error("CLIHandler.start_async_action_unsafe: unable to update database for async action", exc_info=True)
            if async_call is not None:
                async_call.finish(return_value=(AsyncActionOpStatus.DB_FAILED, None))
            logger.debug(f"CLIHandler.start_async_action_unsafe: exit, async_action_op_status={AsyncActionOpStatus.DB_FAILED}, async_action={None}")
            return AsyncActionOpStatus.DB_FAILED, None

        with self.lock:
            # for new action, it should not be in database
            assert async_action.id not in self.async_action_info_dict
            self.async_action_info_dict[async_action.id] = AsyncActionInfo(async_action)
            if async_call is not None:
                async_call.finish(return_value=(AsyncActionOpStatus.OK, async_action))
            # let handler to work in the thread pool
            logger.debug(f"CLIHandler.start_async_action_unsafe: invoking handle in thread pool, handler {found_action_handler.handle}")
            self.executor.submit(found_action_handler.handle, async_action.id, request, self)
            logger.debug(f"CLIHandler.start_async_action_unsafe: exit, async_action_op_status={AsyncActionOpStatus.OK}, async_action={async_action_to_str(async_action)})")
            return AsyncActionOpStatus.OK, async_action

    def start_async_action(
        self, 
        request:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[AsyncActionOpStatus, Optional[AsyncAction]]:
        if self.debug:
            try:
                return self.start_async_action_unsafe(request, async_call=async_call)
            except:
                logger.error("CLIHandler.start_async_action_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.start_async_action_unsafe(request, async_call=async_call)


    def update_progress_async_action_unsafe(
        self, 
        action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> AsyncActionOpStatus:
        #############################################################
        # Update an async action's progress
        #############################################################
        logger.debug(f"CLIHandler.update_progress_async_action_unsafe: enter, action_id={action_id}")
        async_action_info = None

        # persist async action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_async_action = session.get(DBAsyncAction, action_id)
                    if db_async_action is None:
                        if async_call is not None:
                            async_call.finish(return_value=AsyncActionOpStatus.NOT_FOUND)
                        logger.debug(f"CLIHandler.update_progress_async_action_unsafe: exit, status={AsyncActionOpStatus.NOT_FOUND}")
                        return AsyncActionOpStatus.NOT_FOUND
                    
                    if db_async_action.is_completed:
                        if async_call is not None:
                            async_call.finish(return_value=AsyncActionOpStatus.ACTION_COMPLETED)
                        logger.debug(f"CLIHandler.update_progress_async_action_unsafe: exit, status={AsyncActionOpStatus.ACTION_COMPLETED}")
                        return AsyncActionOpStatus.ACTION_COMPLETED
                    
                    db_async_action.updated_at = get_utc_now()
                    db_async_action.progress = progress
                    session.add(db_async_action)
                async_action = AsyncAction.create(db_async_action)
        except SQLAlchemyError:
            logger.error(f"CLIHandler.update_progress_async_action_unsafe: unable to update database for async action with id of {action_id}", exc_info=True)
            if async_call is not None:
                async_call.finish(return_value=AsyncActionOpStatus.DB_FAILED)
            logger.debug("CLIHandler.update_progress_async_action_unsafe: exit, status={AsyncActionOpStatus.DB_FAILED}")
            return AsyncActionOpStatus.DB_FAILED

        logger.debug(f"CLIHandler.update_progress_async_action_unsafe: async action with id of {action_id} is updated in database")

        try:
            assert not self.lock.locked()
            self.lock.acquire()   # this is an expensive global lock
            async_action_info = self.async_action_info_dict[action_id]

            assert not async_action_info.lock.locked()
            async_action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            # handler lock: released
            # async_action_info: locked
            async_action_info.async_action.progress = progress
            for _, client in async_action_info.monitoring_client_dict.items():
                if client.pending_removal:
                    logger.debug(f"CLIHandler.update_progress_async_action_unsafe: not set event for monitoring client of id {client.id} since it is in pending removal mode")
                else:
                    logger.debug(f"CLIHandler.update_progress_async_action_unsafe: set event for monitoring client of id {client.id}")
                    client.pending_removal = True
                    self.event_loop.call_soon_threadsafe(client.event.set)
            
            if async_call is not None:
                async_call.finish(return_value=AsyncActionOpStatus.OK)
            logger.debug(f"CLIHandler.update_progress_async_action_unsafe: exit, status={AsyncActionOpStatus.OK}")
            return AsyncActionOpStatus.OK
        finally:
            if self.lock.locked():
                self.lock.release()
            if async_action_info is not None and async_action_info.lock.locked():
                async_action_info.lock.release()
    
    def update_progress_async_action(
        self, action_id:int, 
        progress:Any, 
        async_call:Optional[AsyncCall]=None
    ) -> AsyncActionOpStatus:
        if self.debug:
            try:
                return self.update_progress_async_action_unsafe(action_id, progress, async_call=async_call)
            except:
                logger.error("CLIHandler.update_progress_async_action_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.update_progress_async_action_unsafe(action_id, progress, async_call=async_call)


    def complete_async_action_unsafe(self, action_id:int, response:Any, async_call:Optional[AsyncCall]=None):
        #############################################################
        # Complete an async action's progress
        #############################################################
        logger.debug(f"CLIHandler.complete_async_action_unsafe: enter, action_id={action_id}")
        async_action_info = None
        
        # persist async action
        try:
            with Session(self.db_engine) as session:
                with session.begin():
                    db_async_action = session.get(DBAsyncAction, action_id)
                    if db_async_action is None:
                        if async_call is not None:
                            async_call.finish(return_value=AsyncActionOpStatus.NOT_FOUND)
                        logger.debug(f"CLIHandler.complete_async_action_unsafe: exit, status={AsyncActionOpStatus.NOT_FOUND}")
                        return

                    if db_async_action.is_completed:
                        if async_call is not None:
                            async_call.finish(return_value=AsyncActionOpStatus.ACTION_COMPLETED)
                        logger.debug(f"CLIHandler.complete_async_action_unsafe: exit, status={AsyncActionOpStatus.ACTION_COMPLETED}")
                        return

                    db_async_action.is_completed = True
                    db_async_action.completed_at = get_utc_now()
                    db_async_action.response = response
                    session.add(db_async_action)
                async_action = AsyncAction.create(db_async_action)
        except SQLAlchemyError:
            logger.error(f"CLIHandler.complete_async_action_unsafe: unable to update database for async action with id of {action_id}", exc_info=True)
            if async_call is not None:
                async_call.finish(return_value=AsyncActionOpStatus.DB_FAILED)
            logger.debug(f"CLIHandler.complete_async_action_unsafe: exit, status={AsyncActionOpStatus.DB_FAILED}")
            return

        try:
            assert not self.lock.locked()
            self.lock.acquire()   # this is an expensive global lock
            async_action_info = self.async_action_info_dict[action_id]

            assert not async_action_info.lock.locked()
            async_action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            # handler lock: released
            # async_action_info: locked
            async_action_info.async_action.is_completed = True
            async_action_info.async_action.completed_at = async_action.completed_at
            async_action_info.async_action.response = response
            for _, client in async_action_info.monitoring_client_dict.items():
                if client.pending_removal:
                    logger.debug(f"CLIHandler.complete_async_action_unsafe: not set event for monitoring client of id {client.id} since it is in pending removal mode")
                else:
                    logger.debug(f"CLIHandler.complete_async_action_unsafe: set event for monitoring client of id {client.id}")
                    client.pending_removal = True
                    self.event_loop.call_soon_threadsafe(client.event.set)

            if async_call is not None:
                async_call.finish(return_value=AsyncActionOpStatus.OK)
            logger.debug(f"CLIHandler.complete_async_action_unsafe: exit, status={AsyncActionOpStatus.OK}")
        finally:
            if self.lock.locked():
                self.lock.release()
            if async_action_info is not None and async_action_info.lock.locked():
                async_action_info.lock.release()
        

    def complete_async_action(self, action_id:int, response:Any, async_call:Optional[AsyncCall]=None):
        if self.debug:
            try:
                return self.complete_async_action_unsafe(action_id, response, async_call=async_call)
            except:
                logger.error("CLIHandler.complete_async_action_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.complete_async_action_unsafe(action_id, response, async_call=async_call)

    def remove_monitoring_client_unsafe(
        self, 
        action_id:int, 
        moniroting_client_id: uuid.UUID, 
        async_call:Optional[AsyncCall]=None
    ):
        #############################################################
        # Remove a monitoring client that is no longer needed
        #############################################################
        logger.debug(f"CLIHandler.remove_monitoring_client_unsafe: enter, action_id={action_id}, moniroting_client_id={moniroting_client_id}")
        async_action_info = None
        
        try:
            assert not self.lock.locked()
            self.lock.acquire()
            async_action_info = self.async_action_info_dict.get(action_id)

            if async_action_info is None:
                logger.warning(f"CLIHandler.remove_monitoring_client_unsafe: async action with id of {action_id} does not exist")
                async_call.finish()
                logger.debug("CLIHandler.remove_monitoring_client_unsafe: exit")
                return

            assert not async_action_info.lock.locked()
            async_action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            monitoring_client = async_action_info.monitoring_client_dict.pop(moniroting_client_id, None)
            if monitoring_client is None:
                logger.warning(f"CLIHandler.remove_monitoring_client_unsafe: async action with id of {action_id} does not have monitoring client of id {moniroting_client_id}")
                async_call.finish()
                logger.debug("CLIHandler.remove_monitoring_client_unsafe: exit")
                return
            
            assert monitoring_client.async_action.id == action_id
            async_call.finish()
            logger.debug("CLIHandler.remove_monitoring_client_unsafe: exit")
        finally:
            if self.lock.locked():
                self.lock.release()
            if async_action_info is not None and async_action_info.lock.locked():
                async_action_info.lock.release()

        logger.debug("CLIHandler.remove_monitoring_client_unsafe: exit")

    def remove_monitoring_client(
        self, 
        action_id:int, 
        moniroting_client_id: uuid.UUID, 
        async_call:Optional[AsyncCall]=None
    ):
        if self.debug:
            try:
                return self.remove_monitoring_client_unsafe(action_id, moniroting_client_id, async_call=async_call)
            except:
                logger.error("CLIHandler.remove_monitoring_client_unsafe: exception captured", exc_info=True)
                raise
        else:
            return self.remove_monitoring_client_unsafe(action_id, moniroting_client_id, async_call=async_call)


    def register_monitor_async_action_unsafe(
        self, 
        action_id:int, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[AsyncActionOpStatus, AsyncActionMonitoringClient]:
        #############################################################
        # Register a client, so the client can monitor if the async action is
        # completed or any updates
        #############################################################
        logger.debug(f"CLIHandler.register_monitor_async_action_unsafe: enter, action_id={action_id}")
        async_action_info = None

        try:
            assert not self.lock.locked()
            self.lock.acquire()   # this is an expensive global lock
            async_action_info = self.async_action_info_dict.get(action_id)
            if async_action_info is None:
                async_call.finish(return_value=(AsyncActionOpStatus.NOT_FOUND, None))
                logger.debug(f"CLIHandler.register_monitor_async_action_unsafe: exit, status={AsyncActionOpStatus.NOT_FOUND}, monitoring_client=None")
                return AsyncActionOpStatus.NOT_FOUND, None

            assert not async_action_info.lock.locked()
            async_action_info.lock.acquire()  # this lock is per async action, which is not expensive
            self.lock.release()

            # handler lock: released
            # async_action_info: locked
            if async_action_info.async_action.is_completed:
                async_call.finish(return_value=(AsyncActionOpStatus.ACTION_COMPLETED, None))
                logger.debug(f"CLIHandler.register_monitor_async_action_unsafe: exit, status={AsyncActionOpStatus.ACTION_COMPLETED}, monitoring_client=None")
                return AsyncActionOpStatus.ACTION_COMPLETED, None
            
            monitoring_client = async_action_info.create_client_unsafe()
            async_call.finish(return_value=(AsyncActionOpStatus.OK, monitoring_client))
            logger.debug(f"CLIHandler.register_monitor_async_action_unsafe: exit, status={AsyncActionOpStatus.OK}, monitoring_client={monitoring_client_to_str(monitoring_client)}")
            return AsyncActionOpStatus.OK, monitoring_client
        finally:
            if self.lock.locked():
                self.lock.release()
            if async_action_info is not None and async_action_info.lock.locked():
                async_action_info.lock.release()

    def register_monitor_async_action(
        self, 
        action_id:int, 
        async_call:Optional[AsyncCall]=None
    ) -> Tuple[AsyncActionOpStatus, AsyncActionMonitoringClient]:
        if self.debug:
            try:
                return self.register_monitor_async_action_unsafe(action_id, async_call=async_call)
            except:
                logger.error("CLIHandler.register_monitor_async_action: exception captured", exc_info=True)
                raise
        else:
            return self.register_monitor_async_action_unsafe(action_id, async_call=async_call)

