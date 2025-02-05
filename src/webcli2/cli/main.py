import os
import yaml
import logging
import logging.config        
import uvicorn
import argparse
from sqlalchemy import create_engine
from webcli2.db_models import create_all_tables
import getpass

from webcli2.config import WebCLIApplicationConfig, load_config, normalize_filename
from webcli2.webcli_engine import UserManager

logger = None

class WebCLIApplication:
    webcli_home:str                     # WebCLI application home directory
    config_filename:str                 # WebCLI config file name, it is a YAML file
    config:WebCLIApplicationConfig      # config loaded from webcli_cfg.yaml
    
    def initialize_logging(self):
        # create loging directory
        os.makedirs(self.config.core.log_dir, exist_ok=True)

        # loading logging config
        if not os.path.isfile(self.config.core.log_config_filename):
            print(f"Missing log config file: {self.config.core.log_config_filename}")
            exit(1)
        with open(self.config.core.log_config_filename, "rt") as f:
            global logger
            log_config = yaml.safe_load(f)
        # patch filename field
        for _, handler_config in log_config.get("handlers", {}).items():
            if "filename" in handler_config:
                handler_config["filename"] = normalize_filename(
                    self.config.core.log_dir, 
                    handler_config["filename"]
                )
        logging.config.dictConfig(log_config)
        
        logger = logging.getLogger(__file__)
        logger.info("Logging is initialized")


    def initialize(self):
        self.config = load_config()
        if self.config is None:
            print(f"Missing config file")
            exit(1)

        self.initialize_logging()
        

    def start(self):
        self.initialize()
        from webcli2.web import app
        # run application
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)

def webcli():
    parser = argparse.ArgumentParser(
        description='WebCLI Tool.'
    )
    parser.add_argument(
        "action", type=str, help="Specify action",
        choices=['start', 'init-db', 'create-user', 'test'],
        nargs=1
    )
    parser.add_argument(
        "--email", type=str, required=False, help="user email"
    )
    args = parser.parse_args()
    action = args.action[0]
    if action == "start":
        webcli_application = WebCLIApplication()
        webcli_application.start()
        return
    
    if action == "init-db":
        initialize_db()
        return
    
    if action == "create-user":
        create_user(args)
        return

    # if action == "test":
    #     test(args)
    #     return

def initialize_db():
    config = load_config()
    db_engine = create_engine(config.core.db_url)
    create_all_tables(db_engine)

def create_user(args):
    password1 = getpass.getpass("Enter your password: ")
    password2 = getpass.getpass("Enter your password again: ")
    if password1 != password2:
        print("Mismatched password")
        exit(1)

    config = load_config()
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
