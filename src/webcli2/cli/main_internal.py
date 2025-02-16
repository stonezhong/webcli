import logging
logger = logging.getLogger(__name__)

import argparse
import getpass

from sqlalchemy import create_engine

from webcli2.config import WebCLIApplicationConfig, load_config, normalize_filename
from webcli2.webcli_engine import UserManager
from webcli2.db_models import create_all_tables

class WebCLIApplication:
    config:WebCLIApplicationConfig      # config loaded from webcli_cfg.yaml
    
    def __init__(self, config:WebCLIApplicationConfig):
        self.config = config

    def start(self, log_config:dict, args:argparse.Namespace):
        import uvicorn
        from webcli2.web import app
        # run application
        uvicorn.run(app, host=args.host, port=args.port, reload=False, log_config=log_config)

def webcli_internal(config:WebCLIApplicationConfig, log_config:dict):
    parser = argparse.ArgumentParser(
        description='WebCLI Tool.'
    )
    parser.add_argument(
        "action", type=str, help="Specify action",
        choices=['start', 'init-db', 'create-user', 'test'],
        nargs=1
    )
    parser.add_argument(
        "--port", type=int, required=False, default=8000, help="Web Server binding port number"
    )
    parser.add_argument(
        "--host", type=str, required=False, default="127.0.0.1", help="Web Server binding IP address"
    )
    parser.add_argument(
        "--email", type=str, required=False, help="user email"
    )
    args = parser.parse_args()
    action = args.action[0]
    if action == "start":
        webcli_application = WebCLIApplication(config)
        webcli_application.start(log_config, args)
        return
    
    if action == "init-db":
        initialize_db(config)
        return
    
    if action == "create-user":
        create_user(config, args)
        return

    if action == "test":
        test(config, args)
        return

def initialize_db(config:WebCLIApplicationConfig):
    db_engine = create_engine(config.core.db_url)
    create_all_tables(db_engine)

def create_user(config:WebCLIApplicationConfig, args:argparse.Namespace):
    password1 = getpass.getpass("Enter your password: ")
    password2 = getpass.getpass("Enter your password again: ")
    if password1 != password2:
        print("Mismatched password")
        exit(1)

    db_engine = create_engine(config.core.db_url)
    um = UserManager(
        db_engine=db_engine, 
        private_key=config.core.private_key, 
        public_key=config.core.public_key
    )
    user = um.create_user(email=args.email, password=password1)
    if user is None:
        print(f"Unable to create user")
        exit(1)

    print(f"User created, id={user.id}, email={user.email}")

# def test(args):
#     jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InN0b25lemhvbmdAaG90bWFpbC5jb20iLCJwYXNzd29yZF92ZXJzaW9uIjoxLCJzdWIiOiIxIiwidXVpZCI6ImFmNmM4Yjc1LTM5ZjctNGVhMS04NjczLTgyYWI1ZTA5YTdjZSJ9.Aea_3-oxSBHHVXFS9ZB0jlo6qKKQDkDWzf_0o0exxEE6HUxLn7oRJSm5m2JVVeJy6cueXBbEAOY7urLw-HaHo4oCFaKIxPHUVurto99ITw84WSUgxQh58uN4H-Qt1-XiZTqALtu1CFL5ZfFXQMEX0KvxXLJ11nSr2c9uAzO6WmznAVXrKymvzTcae3Q992inPjaj9AJtFpPY5WZ_BH7iZ6MaQNogyFLFq8zuQMTSxm0WIgCBAbZmsUN1Brrwrgt7OY-I-lTQAgzmxMddyi-JtcKYH9jIAyQ8klpaMfM4u8K7Wxl4js8Bd-0JWjVxyKFwEwdDo32sMC9Jg-qql4D7_Q"
#     config = load_config()
#     db_engine = create_engine(config.core.db_url)
#     um = UserManager(
#         db_engine=db_engine, 
#         private_key=config.core.private_key, 
#         public_key=config.core.public_key
#     )
#     t = um.extract_payload_from_jwt_token(jwt_token)
#     print(t)

# def test(args):
#     from sqlalchemy import Engine, select, func
#     from sqlalchemy.orm import Session
#     from webcli2.db_models import DBAction, DBActionHandlerConfiguration, DBUser, DBThread, DBThreadAction
#     config = load_config()
#     db_engine = create_engine(config.core.db_url)
#     with Session(db_engine) as session:
#         with session.begin():
#             q = select(
#                 func.max(DBThreadAction.display_order)
#             ).where(DBThreadAction.thread_id == 11)

#             v = session.scalars(q).one()
#             print(v)




def test(config:WebCLIApplicationConfig, args:argparse.Namespace):
    from sqlalchemy.orm import Session
    from sqlalchemy import func
    from sqlalchemy import Engine, select, delete
    from webcli2.web.main import config_action_handlers, action_handlers, webcli_engine
    from webcli2.db_models import DBAction, DBThreadAction, DBActionResponseChunk
    from webcli2.models import ActionResponseChunk
    import datetime

    with Session(webcli_engine.db_engine) as session:
        with session.begin():
            # db_action = DBAction(
            #     user_id=1, 
            #     handler_name="mermaid", 
            #     is_completed=True,
            #     created_at = datetime.datetime.utcnow(),
            #     request={},
            #     title="blah",
            #     raw_text="blah"
            # )
            # session.add(db_action)

            # db_thread_action = DBThreadAction(
            #     thread_id=1,
            #     action_id=1,
            #     display_order=1,
            #     show_question=True,
            #     show_answer=True
            # )
            # session.add(db_thread_action)

            # db_action_response_chunk = DBActionResponseChunk(
            #     action_id=1,
            #     order=1,
            #     mime="text/plain",
            #     text_content="Hello",
            #     binary_content=None
            # )
            # session.add(db_action_response_chunk)

            q = select(
                func.max(DBActionResponseChunk.order)
            ).where(DBActionResponseChunk.action_id == 2)
            v = session.scalars(q).one()

            print(v)

        # ac = ActionResponseChunk.create(dac)

            

        # print(db_action_response_chunk.id)
        # print(ac)


