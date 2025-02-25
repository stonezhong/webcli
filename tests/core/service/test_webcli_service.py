import logging
logger = logging.getLogger(__name__)

for logger_name in ["asyncio", "webcli2.core.service.webcli_service"]:
    logging.getLogger(logger_name).disabled = True


from typing import Any, Generator, Dict
import tempfile
import importlib
import os
import pytest
from unittest.mock import MagicMock, patch, ANY

from sqlalchemy import create_engine
from webcli2.core.data import ObjectNotFound
from webcli2.core.service import WrongPassword

PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCT2NOiinxmnYEZ
mlovwPNzvl5bZSBz015kJ6I+VsdM/A56QwZTMFktY0TX58Xw0ATzqwvRNzdtCQfG
nvuUHjl6Wnv2333USTkqFmB5Y72sA6o6i4N0vtIlCgG6XnI5Cn75pVRnCOjf2GlT
BeAcs7RFhc45+2xCubmQ75TRpbPQ3MMH+VBKpQcnHp+MVpM6tsWvOtnteYZ6cCN1
vn0S6OorKV35dCVs5YirhAeCZoD/GdATTdLueRIbRWYpZv3GHGlDcxkm8enbVZqu
890AvIUnnelByeR6hicEC4SVz8xKUtcgYWe60BHx8uhDMD1GNNmwhziZWkPBE3Hv
FB/KfG+/AgMBAAECggEAMZPVkB1hTuXFK2k7keThnm/5Yyt7oOuBrRMvUDk4VuP1
FOGR5uaBGPu/U6k4kqKm7nDuowchknIjReL9GPOzsYhTJntWThAJ18euLTaZnWuT
M1OiTs1IWbxLzQurwN34q01aCr0NnjaLRxhiyS0np+KRP5dEe/GcvPHiFRU8Qa6r
SUfm3g7yY2S6M6pPp9S3NOOeAx9MkYusKZhKpeH8ZDuODFwUcdoKO+YTkf9+1b/N
T1kaJY1NDvtlGTFXnv2NncJKIDcRI81e4T8BkXy7DnssbNfoo0fvCp+NqV/0eGh2
23sl4ociZoG6QV+AnG4mvTHVIC0/6V/3HA1IEu4iPQKBgQDE7Ejm61wy3UNYW3uB
DrAU/y3pTWjHp6PIQ499IdbABrq0N8KEy+SBM+gxfJYDEglDTKMIg1PYwu253rS0
2uYCBurKSGpExXd7KFy0Bia+osA7Jekk3iCCGMy1C9XRqYy/MTCXDHEetEgw9mOs
gwJMuGVF0tjkJ9hTkvuXhmY9WwKBgQDAM39Afb4RvOGgJfDPS2XazAJ9+xFuMrG6
/59bApDfDrC+V09EZ/c/vkpCgdan87tj/2XaZh6bL5nvslMsrCHXhYBt026f+pv9
odaefflrOY8+dHOZcP+jPyUQQrUtWTjF3QG/7Zg18Lgb7VKM3GWHmdipdqp4KhjQ
I0ew5n3wbQKBgCCie+5xAOWZD6kb+BrKQVopdAVfA8dau+TbdXMqYXmPY++r8fuq
AqN647cXy5CUs55InBg0E3gvzc/o3Y+/WzDozo5Zc+sTwppRdROMlW0wcaUbwkiO
21pUG9DBNl05uQ6Sa1gNAs4w2Gns21XinEX0pSvuJm2hQNOQ30scReNTAoGAVHNM
Ko4Vgb24daG2GZ9LdcPGJIy4r+7eYQgIgPizpw7RYhEC50+3N+7ouihKpSlW4S1L
F5dfQ1i7DrMQEMThac1jDN6l8O0wtVTy9FjtystTwWFxma4o5RXNt0NYUECvzWC6
cBZ5ltnaS4sPho0gn2Bd7rgRVxNIK8wUqAnetFECgYAZFZJrkQ5VP2hybRRMXIjG
ZUDqKnGwM5hmFe97yP1KD7Iq/X5bYCfWmulUybRciO/Y47YwCl6H/u2qe+Ua6DHi
twQC1nnUmjAciFffH0gsS3wAG58dZAItexIDV3cIskO2wMjpe4h9blrdiI6+7PGL
H6OBEK1PSf07i6NF83CW2w==
-----END PRIVATE KEY-----
"""

PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAk9jToop8Zp2BGZpaL8Dz
c75eW2Ugc9NeZCeiPlbHTPwOekMGUzBZLWNE1+fF8NAE86sL0Tc3bQkHxp77lB45
elp79t991Ek5KhZgeWO9rAOqOouDdL7SJQoBul5yOQp++aVUZwjo39hpUwXgHLO0
RYXOOftsQrm5kO+U0aWz0NzDB/lQSqUHJx6fjFaTOrbFrzrZ7XmGenAjdb59Eujq
Kyld+XQlbOWIq4QHgmaA/xnQE03S7nkSG0VmKWb9xhxpQ3MZJvHp21WarvPdALyF
J53pQcnkeoYnBAuElc/MSlLXIGFnutAR8fLoQzA9RjTZsIc4mVpDwRNx7xQfynxv
vwIDAQAB
-----END PUBLIC KEY-----
"""

# @pytest.fixture
# def mock_da() -> Generator[Any]:
#     with patch('webcli2.core.data.DataAccessor') as MockDataAccessor:
#         _mock_da = MagicMock()
#         MockDataAccessor.return_value = _mock_da
#         yield _mock_da

@pytest.fixture
def webcli_service() -> Generator["WebCLIService"]:
    from webcli2.core.service import WebCLIService
    from webcli2.config import ActionHandlerInfo
    from webcli2.core.data import create_all_tables

    action_handlers = { }
    action_handlers_config:Dict[str, ActionHandlerInfo] = {
        "system": ActionHandlerInfo(
            module_name="webcli2.action_handlers.system",
            class_name="SystemActionHandler",
            config = {}
        )
    }
    for action_handler_name, action_handler_info in action_handlers_config.items():
        module = importlib.import_module(action_handler_info.module_name)
        klass = getattr(module, action_handler_info.class_name)
        action_handler = klass(**action_handler_info.config)
        action_handlers[action_handler_name] = action_handler

    with tempfile.TemporaryDirectory() as tmpdirname:
        # first create a db 
        db_filename = os.path.join(tmpdirname, "webcli.db")
        db_url = f"sqlite:///{db_filename}"
        db_engine = create_engine(db_url, connect_args={"check_same_thread": False})
        create_all_tables(db_engine)

        users_home_dir = os.path.join(tmpdirname, "users")
        resource_dir = os.path.join(tmpdirname, "resources")
        os.makedirs(users_home_dir)
        os.makedirs(resource_dir)

        service = WebCLIService(
            users_home_dir = users_home_dir,
            resource_dir = resource_dir,
            public_key=PUBLIC_KEY,
            private_key=PRIVATE_KEY,
            db_engine=db_engine,
            action_handlers = action_handlers
        )
        service.startup()
        yield service
        service.shutdown()


def test_create_user(webcli_service):
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        mock_da = MagicMock()
        MockDataAccessor.return_value = mock_da
        mock_user = MagicMock()
        mock_da.create_user.return_value = mock_user
    
        user = webcli_service.create_user(email="foo@abc.com", password="abc")

        # it calls DataAccessor.create_user once with email, we are not checking hashed password
        mock_da.create_user.assert_called_once_with(
            email="foo@abc.com", 
            password_hash=ANY
        )
        # the returned user is the same user returned from da.create_user
        assert user is mock_user

def test_login_user_not_found(webcli_service):
    # simulate: user with the email does not exist
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        mock_da = MagicMock()
        MockDataAccessor.return_value = mock_da
        mock_da.get_user_by_email = MagicMock(side_effect=ObjectNotFound())

        with pytest.raises(ObjectNotFound) as exc_info:
            webcli_service.login_user(email="foo@abc.com", password="abc")
            mock_da.get_user_by_email.assert_called_once_with("foo@abc.com")

def test_login_user_wrong_password(webcli_service):
    # simulate: user with the email exist, but password is wrong
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        with patch('webcli2.core.service.webcli_service.bcrypt') as mock_bcrypt:
            mock_da = MagicMock()
            MockDataAccessor.return_value = mock_da
            mock_user = MagicMock(password_hash = "foo")
            mock_da.get_user_by_email.return_value = mock_user

            mock_bcrypt.checkpw.return_value = False

            with pytest.raises(WrongPassword) as exc_info:
                webcli_service.login_user(email="foo@abc.com", password="abc")
                mock_da.get_user_by_email.assert_called_once_with("foo@abc.com")
                mock_bcrypt.checkpw.assert_called_once_with(b"abc", b"foo")

def test_login_user(webcli_service):
    # simulate: user with the email exist, password is correct
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        with patch('webcli2.core.service.webcli_service.bcrypt') as mock_bcrypt:
            mock_da = MagicMock()
            MockDataAccessor.return_value = mock_da
            mock_user = MagicMock(password_hash = "foo")
            mock_da.get_user_by_email.return_value = mock_user

            mock_bcrypt.checkpw.return_value = True

            user = webcli_service.login_user(email="foo@abc.com", password="abc")
            mock_da.get_user_by_email.assert_called_once_with("foo@abc.com")
            mock_bcrypt.checkpw.assert_called_once_with(b"abc", b"foo")
            assert user is mock_user

def test_generate_user_jwt_token(webcli_service):
    with patch('webcli2.core.service.webcli_service.jwt') as mock_jwt:
        mock_jwt.encode.return_value = "foobar"
        from webcli2.core.data import User
        user = User(id=1, is_active=True, email="foo@abc.com", password_version=1, password_hash="**")
        jwt_token = webcli_service.generate_user_jwt_token(user)
        mock_jwt.encode.assert_called_once_with(ANY, PRIVATE_KEY, algorithm="RS256")
        assert "foobar" == jwt_token

def test_list_thread(webcli_service):
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        mock_da = MagicMock()
        MockDataAccessor.return_value = mock_da
        mock_thread1 = MagicMock()
        mock_thread2 = MagicMock()
        mock_da.list_threads.return_value = [mock_thread1, mock_thread2]

        from webcli2.core.data import User
        user = User(id=1, is_active=True, email="foo@abc.com", password_version=1, password_hash="**")
        threads = webcli_service.list_threads(user=user)
        mock_da.list_threads.assert_called_once_with(user=user)
        assert threads == [mock_thread1, mock_thread2]

def test_get_thread(webcli_service):
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        mock_da = MagicMock()
        MockDataAccessor.return_value = mock_da
        mock_thread = MagicMock()
        mock_da.get_thread.return_value = mock_thread

        from webcli2.core.data import User
        user = User(id=1, is_active=True, email="foo@abc.com", password_version=1, password_hash="**")
        thread = webcli_service.get_thread(1, user=user)
        mock_da.get_thread.assert_called_once_with(1, user=user)
        assert thread is mock_thread

def test_patch_thread(webcli_service):
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        mock_da = MagicMock()
        MockDataAccessor.return_value = mock_da
        mock_thread = MagicMock()
        mock_da.patch_thread.return_value = mock_thread

        from webcli2.core.data import User
        user = User(id=1, is_active=True, email="foo@abc.com", password_version=1, password_hash="**")
        thread = webcli_service.patch_thread(1, user=user, title="foo")
        mock_da.patch_thread.assert_called_once_with(1, title="foo", description=None, user=user)
        assert thread is mock_thread

# TODO: create_thread_action
def test_delete_thread(webcli_service):
    with patch('webcli2.core.service.webcli_service.DataAccessor') as MockDataAccessor:
        mock_da = MagicMock()
        MockDataAccessor.return_value = mock_da
        mock_da.delete_thread.return_value = None

        from webcli2.core.data import User
        user = User(id=1, is_active=True, email="foo@abc.com", password_version=1, password_hash="**")
        webcli_service.delete_thread(1, user=user)
        mock_da.delete_thread.assert_called_once_with(1, user=user)

