from typing import Any, Generator
import os
import pytest
import json

import tempfile
from sqlalchemy import create_engine, Engine, select
from sqlalchemy.orm import Session

from webcli2.core.data import create_all_tables, ObjectNotFound, DataAccessor, DuplicateUserEmail, \
    ActionAlreadyInThread
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

@pytest.fixture
def session(db_engine:Engine) -> Session:
    return Session(db_engine)


@pytest.fixture
def da(session:Session) -> DataAccessor:
    return DataAccessor(session)

@pytest.fixture
def user(da:DataAccessor) -> User:
    return da.create_user(email="foo@abc.com", password_hash="abc")

@pytest.fixture
def user2(da:DataAccessor) -> User:
    return da.create_user(email="foo2@abc.com", password_hash="abc")

@pytest.fixture
def thread(da:DataAccessor, user:User) -> Thread:
    return da.create_thread(title="blah", description="blah", user=user)

@pytest.fixture
def thread2(da:DataAccessor, user:User) -> Thread:
    return da.create_thread(title="blah2", description="blah2", user=user)

@pytest.fixture
def action(da:DataAccessor, user:User) -> Action:
    return da.create_action(handler_name="foo", request={}, title="blah", raw_text="hello", user=user)

@pytest.fixture
def action2(da:DataAccessor, user:User) -> Action:
    return da.create_action(handler_name="bar", request={}, title="blah2", raw_text="hello2", user=user)

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
def test_da_create_user(session:Session, da:DataAccessor):
    # happy case
    with session:
        da.create_user(email="foo@abc.com", password_hash="abc")
    
        users = list(session.scalars(select(DBUser).where(DBUser.email == "foo@abc.com")))
        assert len(users) == 1
        user = users[0]
        assert user.email == "foo@abc.com"
        assert user.password_hash == "abc"
        assert user.is_active == True
        assert user.password_version == 1

        # trying to create user with duplicate user with same email
        with pytest.raises(DuplicateUserEmail) as exc_info:
            da.create_user(email="foo@abc.com", password_hash="abc")
            assert exc_info.value.email == "foo@abc.com"

        # make sure transaction is rollbacked upon IntegrityError, otherwise, you won't be able to create a new user
        da.create_user(email="foo2@abc.com", password_hash="abc")

def test_da_get_user(session:Session, da:DataAccessor):
    with session:
        user = da.create_user(email="foo@abc.com", password_hash="abc")

        # we should find the user we just created
        user2 = da.get_user(user.id)
        assert_same_user(user2, user)

        # If user not found, get_user should raise ObjectNotFound exception
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_user(100)

def test_da_get_user_by_email(session:Session, da:DataAccessor, user:User):
    with session:
        user2 = da.get_user_by_email("foo@abc.com")
        assert_same_user(user2, user)

        # wrong user, expect ObjectNotFound exception
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_user_by_email("bar@abc.com")

def test_da_create_thread(session:Session, da:DataAccessor, user:User):
    with session:
        da.create_thread(title="blah", description="blah", user=user)

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

def test_da_get_thread(session:Session, da:DataAccessor, user:User, user2:User, thread:Thread):
    with session:
        # happy case
        thread1 = da.get_thread(thread.id, user=user)
        assert_same_thread(thread1, thread)

        # worng thread_id, raise ObjectNotFound
        # if thread does not exist, get_thread should raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            thread1 = da.get_thread(100, user=user)

        # worng user, raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            thread1 = da.get_thread(thread.id, user=user2)

def test_da_list_thread(session:Session, da:DataAccessor, user:User, thread:Thread, thread2:Thread):
    with session:
        threads = da.list_threads(user=user)
        threads = sorted(threads, key=lambda t:t.title)
        assert len(threads) == 2
        assert_same_thread(thread, threads[0])
        assert_same_thread(thread2, threads[1])

def test_da_create_action(session:Session, da:DataAccessor, user:User, action:Action):
    with session:
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

def test_da_get_action(session:Session, da:DataAccessor, user:User, user2:User, action:Action):
    with session:
        # happy case        
        # get_action return the same action
        action2 = da.get_action(action.id, user=user)
        assert_same_action(action, action2)

        # wrong action id, raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_action(100, user=user)

        # wrong user, raise ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.get_action(action.id, user=user2)

def test_da_patch_action(session:Session, da:DataAccessor, user:User, user2:User, action:Action):
    with session:
        da.patch_action(action.id, user=user, title="bar")
    
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

def test_da_complete_action(session:Session, da:DataAccessor, user:User, user2:User, action:Action):
    with session:
        da.complete_action(action.id, user=user)

        # action should be compelted
        action2 = da.get_action(action.id, user=user)
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
        with pytest.raises(ObjectNotFound) as exc_info:
            da.complete_action(100, user=user)

        # wrong user
        with pytest.raises(ObjectNotFound) as exc_info:
            da.complete_action(action.id, user=user2)

def test_da_append_action_to_thread(
    session:Session, 
    da:DataAccessor, 
    user:User,
    user2:User,
    thread:Thread, 
    action:Action, 
    action2:Action
):
    with session:
        thread_action1 = da.append_action_to_thread(thread_id=thread.id, action_id=action.id, user=user)
        assert thread_action1.thread_id == thread.id
        assert_same_action(thread_action1.action, action)
        assert thread_action1.display_order == 1
        assert thread_action1.show_question == False  # by default, only show answer for newly created thread action
        assert thread_action1.show_answer == True

        # create second thread action for a thread
        thread_action2 = da.append_action_to_thread(thread_id=thread.id, action_id=action2.id, user=user)
        assert thread_action2.thread_id == thread.id
        assert_same_action(thread_action2.action, action2)
        assert thread_action2.display_order == 2
        assert thread_action2.show_question == False  # by default, only show answer for newly created thread action
        assert thread_action2.show_answer == True

        # You cannot add the same action to a thread more than once
        with pytest.raises(ActionAlreadyInThread) as exc_info:
            da.append_action_to_thread(thread_id=thread.id, action_id=action.id, user=user)
            assert exc_info.value.thread_id == thread.id
            assert exc_info.value.action_id == action.id

        # User who do not own an action and/or thread cannot operate
        with pytest.raises(ObjectNotFound) as exc_info:
            da.append_action_to_thread(thread_id=thread.id, action_id=action.id, user=user2)

def test_da_append_response_to_action(session:Session, da:DataAccessor, user:User, action:Action):
    with session:
        da.append_response_to_action(
            action.id,
            mime = "text/plain",
            text_content="hello",
            binary_content=None,
            user=user
        )
        db_action_response_chunkns = list(session.scalars(
            select(DBActionResponseChunk)\
                .where(DBActionResponseChunk.action_id == action.id)\
                .order_by(DBActionResponseChunk.order)
        ))
        assert len(db_action_response_chunkns) == 1
        db_action_response_chunk = db_action_response_chunkns[0]
        assert db_action_response_chunk.action_id == action.id
        assert db_action_response_chunk.order == 1 # this is the first response
        assert db_action_response_chunk.mime == "text/plain"
        assert db_action_response_chunk.text_content == "hello"
        assert db_action_response_chunk.binary_content is None

        # add another one
        da.append_response_to_action(
            action.id,
            mime = "text/plain",
            text_content="hello2",
            binary_content=None,
            user=user
        )
        db_action_response_chunkns = list(session.scalars(
            select(DBActionResponseChunk)\
                .where(DBActionResponseChunk.action_id == action.id)\
                .order_by(DBActionResponseChunk.order)
        ))
        assert len(db_action_response_chunkns) == 2
        db_action_response_chunk = db_action_response_chunkns[1]
        assert db_action_response_chunk.action_id == action.id
        assert db_action_response_chunk.order == 2 # this is the first response
        assert db_action_response_chunk.mime == "text/plain"
        assert db_action_response_chunk.text_content == "hello2"
        assert db_action_response_chunk.binary_content is None

def test_da_remove_action_from_thread(session:Session, da:DataAccessor, user:User, user2:User, thread:Thread, action:Action):
    with session:
        # the common case
        da.append_action_to_thread(thread_id=thread.id, action_id=action.id, user=user)
        r = da.remove_action_from_thread(thread_id=thread.id, action_id=action.id, user=user)
        assert r == True
        thread2 = da.get_thread(thread.id, user=user)
        assert len(thread2.thread_actions) == 0 # after removing the action from thread, the thread has no actions

        # removing an action that is not in the thread, retrun False
        r = da.remove_action_from_thread(thread_id=thread.id, action_id=action.id, user=user)
        assert r == False

        # removing an non existing action id, cause ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.remove_action_from_thread(thread_id=thread.id, action_id=100, user=user)

        # removing an non existing thread id, cause ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.remove_action_from_thread(thread_id=100, action_id=action.id, user=user)

        # removing an non existing thread id, cause ObjectNotFound
        with pytest.raises(ObjectNotFound) as exc_info:
            da.remove_action_from_thread(thread_id=thread.id, action_id=action.id, user=user2)


def test_da_set_action_handler_user_config(session:Session, da:DataAccessor, user:User):
    # no config is set, get_action_handler_user_config should return {}
    with session:
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


def test_da_get_action_handler_user_config(session:Session, da:DataAccessor, user:User):
    with session:
        # no config is set, get_action_handler_user_config should return {}
        config = da.get_action_handler_user_config(
            action_handler_name="pyspark", 
            user=user
        )
        assert config == {}


        # set config, get_action_handler_user_config should return user's config
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

