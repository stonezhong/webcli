import logging
logger = logging.getLogger(__name__)

import argparse
import getpass

from webcli2.config import WebCLIApplicationConfig
from webcli2.service_loader import load_webcli_service

def webcli_internal(config:WebCLIApplicationConfig, log_config:dict):
    parser = argparse.ArgumentParser(
        description='WebCLI Tool.'
    )
    parser.add_argument(
        "action", type=str, help="Specify action",
        choices=['start', 'init-db', 'create-user'],
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
        import uvicorn
        from webcli2.web import app

        ####################################################################################
        # Although we can load WebCLIService here and set it in app.state.webcli_service
        # We choose to let app itself to load service using service loader
        # Since everyone is using the same service loader, the result shuold be the same
        ####################################################################################
        # run application
        uvicorn.run(app, host=args.host, port=args.port, reload=False, log_config=log_config)
        return
    
    if action == "init-db":
        webcli_service = load_webcli_service(config)
        webcli_service.create_all_tables()
        return
    
    if action == "create-user":
        webcli_service = load_webcli_service(config)

        password1 = getpass.getpass("Enter your password: ")
        password2 = getpass.getpass("Enter your password again: ")
        if password1 != password2:
            print("Mismatched password")
            exit(1)

        user = webcli_service.create_user(email=args.email, password=password1)
        print(f"User created, id={user.id}, email={user.email}")
        return


