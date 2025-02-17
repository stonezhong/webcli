from typing import Any, Generator
import os
import pytest
import json

import tempfile
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session

from webcli2.core.data.db_models import create_all_tables, DBUser
from webcli2.core.data import DataAccessor

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
# Test
#     - create a user
#     - query the user by ID, make sure the fields are correct
############################################################################
def test_create_db_user(db_engine:Engine):
    # save a db user and then read it
    with Session(db_engine) as session:
        with session.begin():
            db_user = DBUser(
                is_active = True,
                email = "stonezhong@hotmail.com",
                password_version = 1,
                password_hash = "***"
            )
            session.add(db_user)
        user_id = db_user.id

    with Session(db_engine) as session:
        db_user = session.get(DBUser, user_id)
        assert db_user.id == user_id
        assert db_user.email == "stonezhong@hotmail.com"
        assert db_user.password_version == 1
        assert db_user.password_hash == "***"


def test_case_1(db_engine:Engine):
    with Session(db_engine) as session:
        da = DataAccessor(session)
        # create a user
        user = da.create_user(email="stonezhong@hotmail.com", password_hash="***")

        # create a thread
        thread = da.create_thread(title="foo", description="blah...", user=user)

        # create an action
        action = da.create_action(
            handler_name = "foo",
            request = {},
            title = "question 1",
            raw_text = "%html%\n<h1>Hi</h1>",
            user = user
        )
        # adding action to thread
        da.append_action_to_thread(thread_id=thread.id, action_id=action.id, user=user)

        da.append_response_to_action(
            action.id, 
            mime="text/html", 
            text_content="<h1>Hello</h1>", 
            user=user
        )

        # da.delete_thread(thread.id, user=user)
        thread = da.get_thread(thread.id, user=user)

        print(json.dumps(
            thread.model_dump(mode="json"),
            indent=4
        ))
        
