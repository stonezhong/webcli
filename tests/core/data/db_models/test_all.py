from typing import Any, Generator
import os
import pytest
import json

import tempfile
from sqlalchemy import create_engine, Engine, select
from sqlalchemy.orm import Session

from webcli2.core.data import create_all_tables, ObjectNotFound, DataAccessor, DuplicateUserEmail
from webcli2.core.data.db_models import DBUser, DBThread, DBThreadAction, DBAction, DBActionResponseChunk, \
    DBActionHandlerConfiguration
from webcli2.core.data import User, Thread, Action, ActionResponseChunk

@pytest.fixture
def db_engine() -> Generator[Engine]:
    with tempfile.NamedTemporaryFile(prefix="testdb-", suffix=".db") as f:
        pass
    filename = f.name
    url = f"sqlite:///{f.name}"
    _db_engine = create_engine(url, connect_args={"check_same_thread": True})
    create_all_tables(_db_engine)

    yield _db_engine

    if os.path.isfile(filename):
        os.remove(filename)


############################################################################
# Here are some utility functions
############################################################################
def assert_same_user(user1:User, user2:User):
    assert user1.id == user2.id
    assert user1.email == user2.email
    assert user1.is_active == user2.is_active
    assert user1.password_version == user2.password_version
    assert user1.password_hash == user2.password_hash

def assert_same_thread(thread1:Thread, thread2:Thread):
    assert thread1.id == thread2.id
    assert thread1.created_at == thread2.created_at
    assert thread1.title == thread2.title
    assert thread1.description == thread2.description
    assert_same_user(thread1.user, thread2.user)

def assert_same_action_response_chunk(action_response_chunk1:ActionResponseChunk, action_response_chunk2:ActionResponseChunk):
    assert action_response_chunk1.id == action_response_chunk2.id
    assert action_response_chunk1.action_id == action_response_chunk2.action_id
    assert action_response_chunk1.order == action_response_chunk2.order
    assert action_response_chunk1.mime == action_response_chunk2.mime
    assert action_response_chunk1.text_content == action_response_chunk2.text_content
    assert action_response_chunk1.binary_content == action_response_chunk2.binary_content


def assert_same_action(action1:Action, action2:Action):
    assert action1.id == action2.id
    assert_same_user(action1.user, action2.user)
    assert action1.handler_name == action2.handler_name
    assert action1.is_completed == action2.is_completed
    assert action1.created_at == action2.created_at
    assert action1.completed_at == action2.completed_at
    assert action1.request == action2.request
    assert action1.title == action2.title
    assert action1.raw_text == action2.raw_text

    assert len(action1.response_chunks) == len(action2.response_chunks)
    for i in range(len(action1.response_chunks)):
        response_chunk1 = action1.response_chunks[i]
        response_chunk2 = action2.response_chunks[i]
        assert_same_action_response_chunk(response_chunk1, response_chunk2)

############################################################################
# We are going to test all APIs in DaatAccessor
############################################################################
def test_da_create_user(db_engine:Engine):
    # happy case
    with Session(db_engine) as session:
        da = DataAccessor(session)
        da.create_user(email="foo@abc.com", password_hash="abc")
    
        users = list(session.scalars(select(DBUser).where(DBUser.email == "foo@abc.com")))
        assert len(users) == 1
        user = users[0]
        assert user.email == "foo@abc.com"
        assert user.password_hash == "abc"
        assert user.is_active == True
        assert user.password_version == 1

    # duplicate user with same email
    with Session(db_engine) as session:
        da = DataAccessor(session)
        with pytest.raises(DuplicateUserEmail) as exc_info:
            da.create_user(email="foo@abc.com", password_hash="abc")
            assert exc_info.value.email == "foo@abc.com"


def test_da_get_user(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")

    with Session(db_engine) as session:
        da = DataAccessor(session)

        # we should find the user we just created
        user2 = da.get_user(user.id)
        assert_same_user(user2, user)

        # If user not found, get_user should raise ObjectNotFound exception
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_user(100)

def test_da_get_user_by_email(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")

    # happy case
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user2 = da.get_user_by_email("foo@abc.com")
        assert_same_user(user2, user)


    # wrong user, expect ObjectNotFound exception
    with Session(db_engine) as session:
        da = DataAccessor(session)
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_user_by_email("bar@abc.com")

def test_da_create_thread(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        da.create_thread(title="blah", description="blah", user=user)

    with Session(db_engine) as session:
        threads = list(session.scalars(select(DBThread).where(
            DBThread.user_id == user.id, 
            DBThread.title == "blah", 
            DBThread.description == "blah"
        )))
        assert len(threads) == 1
        thread = threads[0]

        assert thread.title == "blah"
        assert thread.description == "blah"
        assert len(list(session.scalars(select(DBThreadAction).where(DBThreadAction.thread_id == thread.id)))) == 0
        assert_same_user(thread.user, user)

def test_da_get_thread(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        user2 = da.create_user(email="foo1@abc.com", password_hash="abc")
        thread = da.create_thread(title="blah", description="blah", user=user)

    # happy case
    with Session(db_engine) as session:
        thread1 = da.get_thread(thread.id, user=user)
        assert_same_thread(thread1, thread)

    # worng thread_id, raise ObjectNotFound
    with Session(db_engine) as session:
        # if thread does not exist, get_thread should raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            thread1 = da.get_thread(100, user=user)

    # worng user, raise ObjectNotFound
    with Session(db_engine) as session:
        with pytest.raises(ObjectNotFound) as exc_info:
            thread1 = da.get_thread(thread.id, user=user2)

def test_da_list_thread(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        thread1 = da.create_thread(title="blah1", description="blah1", user=user)
        thread2 = da.create_thread(title="blah2", description="blah2", user=user)

    with Session(db_engine) as session:
        threads = da.list_threads(user=user)
        threads = sorted(threads, key=lambda t:t.title)
        assert len(threads) == 2
        assert_same_thread(thread1, threads[0])
        assert_same_thread(thread2, threads[1])

def test_da_create_action(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        action = da.create_action(handler_name="foo", request={}, title="blah", raw_text="hello", user=user)
    
    with Session(db_engine) as session:
        actions = list(session.scalars(select(DBAction).where(
            DBAction.user_id == user.id, 
        )))
        assert len(actions) == 1
        action = actions[0]

        assert_same_user(action.user, user)
        assert action.handler_name == "foo"
        assert action.is_completed == False
        assert action.completed_at == None
        assert action.request == {}
        assert action.title == "blah"
        assert action.raw_text == "hello"

        # newly created action does not have any response chunks
        response_chunks = list(session.scalars(select(DBActionResponseChunk).where(
            DBActionResponseChunk.action_id == action.id, 
        )))
        assert len(response_chunks) == 0

def test_da_get_action(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        user2 = da.create_user(email="foo1@abc.com", password_hash="abc")
        action = da.create_action(handler_name="foo", request={}, title="blah", raw_text="hello", user=user)

    # happy case        
    with Session(db_engine) as session:
        da = DataAccessor(session)
        # get_action return the same action
        action2 = da.get_action(action.id, user=user)
        assert_same_action(action, action2)

    # wrong action id, raise ObjectNotFound
    with Session(db_engine) as session:
        da = DataAccessor(session)
        # if wrong action id, raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_action(100, user=user)

    # wrong user, raise ObjectNotFound
    with Session(db_engine) as session:
        da = DataAccessor(session)
        # if action id is not created by user, raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_action(action.id, user=user2)


def test_da_patch_action(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        action = da.create_action(handler_name="foo", request={}, title="blah", raw_text="hello", user=user)
        da.patch_action(action.id, user=user, title="bar")
    
    with Session(db_engine) as session:
        da = DataAccessor(session)
        action2 = da.get_action(action.id, user=user)
        assert action2.title == "bar"
        assert action2.id == action.id
        assert_same_user(action2.user, action.user)
        assert action2.handler_name == action.handler_name
        assert action2.is_completed == action.is_completed
        assert action2.created_at == action.created_at
        assert action2.completed_at == action.completed_at
        assert action2.request == action.request
        assert action2.raw_text == action.raw_text
        assert len(action2.response_chunks) == 0
        assert len(action.response_chunks) == 0

def test_da_complete_action(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        user2 = da.create_user(email="foo1@abc.com", password_hash="abc")
        action = da.create_action(handler_name="foo", request={}, title="blah", raw_text="hello", user=user)
    
    # complete action
    with Session(db_engine) as session:
        da = DataAccessor(session)
        da.complete_action(action.id, user=user)
        action2 = da.get_action(action.id, user=user)

        # action should be compelted
        assert action2.is_completed == True
        assert action2.completed_at is not None
        assert action.id == action2.id
        assert_same_user(action.user, action2.user)
        assert action.handler_name == action2.handler_name
        assert action.created_at == action2.created_at
        assert action.request == action2.request
        assert action.title == action2.title
        assert action.raw_text == action2.raw_text

        assert len(action.response_chunks) == len(action2.response_chunks)
        for i in range(len(action.response_chunks)):
            response_chunk1 = action.response_chunks[i]
            response_chunk2 = action2.response_chunks[i]
            assert_same_action_response_chunk(response_chunk1, response_chunk2)
    

    # wrong action id
    with Session(db_engine) as session:
        da = DataAccessor(session)
        with pytest.raises(ObjectNotFound) as exc_info:
            da.complete_action(100, user=user)

    # wrong user
    with Session(db_engine) as session:
        da = DataAccessor(session)
        with pytest.raises(ObjectNotFound) as exc_info:
            da.complete_action(action.id, user=user2)

def test_da_set_action_handler_user_config(db_engine:Engine):
    # no config is set, get_action_handler_user_config should return {}
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        da.set_action_handler_user_config(
            action_handler_name="pyspark", 
            user=user,
            config = {"foo": 1}
        )

        db_ahcs = list(session.scalars(
            select(DBActionHandlerConfiguration)\
                .where(DBActionHandlerConfiguration.user_id == user.id)\
                .where(DBActionHandlerConfiguration.action_handler_name == "pyspark")
        ))
        assert len(db_ahcs) == 1
        db_ahc = db_ahcs[0]

        assert db_ahc.action_handler_name == "pyspark"
        assert db_ahc.user_id == user.id
        assert_same_user(User.from_db(db_ahc.user), user)
        assert db_ahc.configuration == {"foo": 1}

    # Now user already have a config set, let's overwrite it
    with Session(db_engine) as session:
        da = DataAccessor(session)
        da.set_action_handler_user_config(
            action_handler_name="pyspark", 
            user=user,
            config = {"bar": 1}
        )

        db_ahcs = list(session.scalars(
            select(DBActionHandlerConfiguration)\
                .where(DBActionHandlerConfiguration.user_id == user.id)\
                .where(DBActionHandlerConfiguration.action_handler_name == "pyspark")
        ))
        assert len(db_ahcs) == 1
        db_ahc = db_ahcs[0]

        assert db_ahc.action_handler_name == "pyspark"
        assert db_ahc.user_id == user.id
        assert_same_user(User.from_db(db_ahc.user), user)
        assert db_ahc.configuration == {"bar": 1}



def test_da_get_action_handler_user_config(db_engine:Engine):
    # no config is set, get_action_handler_user_config should return {}
    with Session(db_engine) as session:
        da = DataAccessor(session)
        user = da.create_user(email="foo@abc.com", password_hash="abc")
        config = da.get_action_handler_user_config(
            action_handler_name="pyspark", 
            user=user
        )
        assert config == {}


    # set config, get_action_handler_user_config should return user's config
    with Session(db_engine) as session:
        da = DataAccessor(session)
        da.set_action_handler_user_config(
            action_handler_name="pyspark", 
            user=user,
            config = {"foo": 1}
        )
        config = da.get_action_handler_user_config(
            action_handler_name="pyspark", 
            user=user
        )
        assert config=={"foo": 1}

