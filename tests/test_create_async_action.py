import logging
logger = logging.getLogger(__name__)

from typing import Any
import tempfile
import os
from datetime import datetime
import asyncio
import time

from unittest.mock import patch, ANY, MagicMock
import pytest
import pytest_asyncio

from webcli2 import CLIHandler, AsyncActionHandler, AsyncActionOpStatus
from webcli2.db_models import create_all_tables, DBAsyncAction
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

class MyTestActionHandler(AsyncActionHandler):
    def can_handle(self, request:Any) -> bool:
        return True

    def handle(self, action_id:int, request:Any, cli_handler: "CLIHandler"):
        pass

@pytest.fixture(scope='function')
def db_engine():
    
    # create a temp file for the db
    f = tempfile.NamedTemporaryFile(prefix="testdb-", suffix=".db")
    f.close()

    db_url = f"sqlite:///{f.name}"
    _db_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    create_all_tables(_db_engine)
    logger.debug("engine is created")

    yield _db_engine

    os.remove(f.name)

@pytest.fixture(scope='function')    
def action_handler():
    _action_handler = MagicMock()
    yield _action_handler

@pytest_asyncio.fixture(scope='function')
async def cli_handler(db_engine, action_handler):
    _cli_handler = CLIHandler(db_engine=db_engine, debug=True, action_handlers=[action_handler])
    _cli_handler.startup()
    yield _cli_handler
    _cli_handler.shutdown()

@pytest_asyncio.fixture(scope='function')
async def cli_handler_with_scavenger(db_engine, action_handler):
    _cli_handler = CLIHandler(db_engine=db_engine, debug=True, action_handlers=[action_handler], run_scavenger=True)
    _cli_handler.startup()
    yield _cli_handler
    _cli_handler.shutdown()


################################################################################
# Scenario: Create async action basic case
#     calling async_start_async_action from async function
#     Create an async action
#     with a handler that can handle it
#     the handler does nothing
################################################################################
@patch('webcli2.main.get_utc_now')
@pytest.mark.asyncio
async def test_async_start_async_action_with_dummy_handler(get_utc_now, cli_handler, action_handler):
    get_utc_now.return_value = datetime(2024, 1,1 )
    action_handler.can_handle.return_value = True
    status, async_action = await cli_handler.async_start_async_action({"foo":1})
    assert status ==  AsyncActionOpStatus.OK

    with Session(cli_handler.db_engine) as session:
        db_async_actions = session.query(DBAsyncAction).all()
        assert len(db_async_actions) == 1
        db_async_action = db_async_actions[0]

        assert db_async_action.id == 1
        assert db_async_action.is_completed == False
        assert db_async_action.created_at == datetime(2024, 1,1)
        assert db_async_action.completed_at is None
        assert db_async_action.updated_at is None
        assert db_async_action.request == {"foo": 1}
        assert db_async_action.response is None
        assert db_async_action.progress is None

    action_handler.can_handle.assert_called()
    action_handler.can_handle.assert_called_with({"foo": 1})
    action_handler.handle.assert_called_with(1, {"foo": 1}, cli_handler)

    assert async_action.id == 1
    assert async_action.is_completed == False
    assert async_action.created_at == datetime(2024, 1,1)
    assert async_action.completed_at is None
    assert async_action.updated_at is None
    assert async_action.request == {"foo": 1}
    assert async_action.response is None
    assert async_action.progress is None

################################################################################
# Scenario: Create async action basic case
#     calling start_async_action (non async way)
#     Create an async action
#     with a handler that can handle it
#     the handler does nothing
################################################################################
@patch('webcli2.main.get_utc_now')
@pytest.mark.asyncio
async def test_start_async_action_with_dummy_handler(get_utc_now, cli_handler, action_handler):
    get_utc_now.return_value = datetime(2024, 1,1 )
    action_handler.can_handle.return_value = True
    status, async_action = cli_handler.start_async_action({"foo":1})
    assert status ==  AsyncActionOpStatus.OK

    with Session(cli_handler.db_engine) as session:
        db_async_actions = session.query(DBAsyncAction).all()
        assert len(db_async_actions) == 1
        db_async_action = db_async_actions[0]

        assert db_async_action.id == 1
        assert db_async_action.is_completed == False
        assert db_async_action.created_at == datetime(2024, 1,1)
        assert db_async_action.completed_at is None
        assert db_async_action.updated_at is None
        assert db_async_action.request == {"foo": 1}
        assert db_async_action.response is None
        assert db_async_action.progress is None

    action_handler.can_handle.assert_called()
    action_handler.can_handle.assert_called_with({"foo": 1})
    action_handler.handle.assert_called_with(1, {"foo": 1}, cli_handler)

    assert async_action.id == 1
    assert async_action.is_completed == False
    assert async_action.created_at == datetime(2024, 1,1)
    assert async_action.completed_at is None
    assert async_action.updated_at is None
    assert async_action.request == {"foo": 1}
    assert async_action.response is None
    assert async_action.progress is None


################################################################################
# Scenario: Create async action basic case
#     Create an async action
#     no handler can handle it
################################################################################
@pytest.mark.asyncio
async def test_async_start_async_action_with_no_handler(cli_handler, action_handler):
    action_handler.can_handle.return_value = False
    status, async_action = await cli_handler.async_start_async_action({"foo":1})
    assert status ==  AsyncActionOpStatus.NO_HANDLER
    assert async_action is None

################################################################################
# Scenario: Create async action basic case
#     Create an async action
#     no handler can handle it
################################################################################
@pytest.mark.asyncio
async def test_start_async_action_with_no_handler(cli_handler, action_handler):
    action_handler.can_handle.return_value = False
    status, async_action = cli_handler.start_async_action({"foo":1})
    assert status ==  AsyncActionOpStatus.NO_HANDLER
    assert async_action is None

####################################################################################
# Scenario: 
# - Create an async action
# - the action handler update the progress of the async action
# - caller call async_wait_for_update_async_action to wait on action's update
####################################################################################
@patch('webcli2.main.get_utc_now')
@pytest.mark.asyncio
async def test_async_wait_for_update_async_action_1(get_utc_now, cli_handler, action_handler):
    get_utc_now.return_value = datetime(2024, 1,1 )

    def handle_action(action_id, request, cli_handler):
        cli_handler.update_progress_async_action(action_id, {"foo": "in-progress"})

    action_handler.can_handle.return_value = True
    action_handler.handle = MagicMock(wraps=handle_action)
    status, async_action = await cli_handler.async_start_async_action({"foo":1})
    assert status == AsyncActionOpStatus.OK

    status, async_action = await cli_handler.async_wait_for_update_async_action(async_action.id, 10)
    assert status == AsyncActionOpStatus.OK

    with Session(cli_handler.db_engine) as session:
        db_async_actions = session.query(DBAsyncAction).all()
        assert len(db_async_actions) == 1
        db_async_action = db_async_actions[0]

        assert db_async_action.id == 1
        assert db_async_action.is_completed == False
        assert db_async_action.created_at == datetime(2024,1,1)
        assert db_async_action.completed_at is None
        assert db_async_action.updated_at == datetime(2024,1,1)
        assert db_async_action.request == {"foo": 1}
        assert db_async_action.response is None
        assert db_async_action.progress == {"foo": "in-progress"}


####################################################################################
# Scenario: 
# - Create an async action
# - the action handler complete the action after 1 second
# - caller call async_wait_for_update_async_action to wait on action's update
####################################################################################
@patch('webcli2.main.get_utc_now')
@pytest.mark.asyncio
async def test_async_wait_for_update_async_action_2(get_utc_now, cli_handler, action_handler):
    get_utc_now.return_value = datetime(2024, 1,1 )

    def handle_action(action_id, request, cli_handler):
        time.sleep(1)
        cli_handler.complete_async_action(action_id, {"foo": "done"})

    action_handler.can_handle.return_value = True
    action_handler.handle = MagicMock(wraps=handle_action)
    status, async_action = await cli_handler.async_start_async_action({"foo":1})
    assert status == AsyncActionOpStatus.OK

    status, async_action = await cli_handler.async_wait_for_update_async_action(async_action.id, 10)
    assert status == AsyncActionOpStatus.OK

    with Session(cli_handler.db_engine) as session:
        db_async_actions = session.query(DBAsyncAction).all()
        assert len(db_async_actions) == 1
        db_async_action = db_async_actions[0]

        assert db_async_action.id == 1
        assert db_async_action.is_completed == True
        assert db_async_action.created_at == datetime(2024,1,1)
        assert db_async_action.completed_at == datetime(2024,1,1)
        assert db_async_action.updated_at is None
        assert db_async_action.request == {"foo": 1}
        assert db_async_action.response == {"foo": "done"}
        assert db_async_action.progress == None

####################################################################################
# Scenario: 
# - Create an async action
# - the action handler does nothing
# - caller call async_wait_for_update_async_action to wait on action's update and timeout
####################################################################################
@patch('webcli2.main.get_utc_now')
@pytest.mark.asyncio
async def test_async_wait_for_update_async_action_3(get_utc_now, cli_handler, action_handler):
    get_utc_now.return_value = datetime(2024, 1,1 )

    def handle_action(action_id, request, cli_handler):
        pass

    action_handler.can_handle.return_value = True
    action_handler.handle = MagicMock(wraps=handle_action)
    status, async_action = await cli_handler.async_start_async_action({"foo":1})
    assert status == AsyncActionOpStatus.OK

    status, async_action = await cli_handler.async_wait_for_update_async_action(async_action.id, 10)
    assert status == AsyncActionOpStatus.TIMEDOUT
    assert async_action is None

####################################################################################
# Scenario: 
# - Create CLI Handler with run_scavenger set to true
####################################################################################
@pytest.mark.asyncio
async def test_scavenger(cli_handler_with_scavenger):
    pass

    
def test_get_utc_now():
    from webcli2.main import get_utc_now
    dt = get_utc_now()
    assert dt.tzinfo is None