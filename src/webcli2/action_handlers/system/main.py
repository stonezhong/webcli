from __future__ import annotations  # Enables forward declaration

import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal, Dict, Union, BinaryIO, TextIO
import threading
import code
import argparse
import shlex
import json
import os
import io
from contextvars import ContextVar
from contextlib import redirect_stdout, redirect_stderr

from pydantic import BaseModel, ValidationError

from webcli2 import ActionHandler
from pydantic import ValidationError
from webcli2.core.data import User

class PythonTheradContext:
    user:User
    action_id:int
    service: Any

    def __init__(self, user:User, action_id:int, service:Any):
        self.user = user
        self.action_id = action_id
        self.service = service

python_thread_context_var = ContextVar("python_thread_context", default=None)

def get_python_thread_context():
    return python_thread_context_var.get()

GLOBAL_II_DICT: Dict[int, code.InteractiveInterpreter] = {}
GLOBAL_II_DICT_LOCK = threading.Lock()

def cli_print(content:Union[str, bytes], *, mime:str="text/html"):
    python_thread_context:PythonTheradContext = python_thread_context_var.get()
    service = python_thread_context.service
    action_id = python_thread_context.action_id
    user = python_thread_context.user

    if isinstance(content, str):
        service.append_response_to_action(
            action_id,
            mime = mime,
            text_content = content,
            user = user
        )
    else:
        service.append_response_to_action(
            action_id,
            mime = mime,
            binary_content = content,
            user = user
        )

def run_code(oatc:PythonTheradContext, locals:dict, source_code):
    my_locals = locals.copy()

    # create an ii if not exist
    with GLOBAL_II_DICT_LOCK:
        user = oatc.user
        # we will create stdout if needed
        # we will create ii if needed
        if user.id not in GLOBAL_II_DICT:
            ii = code.InteractiveInterpreter(locals=my_locals)
            GLOBAL_II_DICT[user.id] = ii
        else:
            ii = GLOBAL_II_DICT[user.id]
    
    # now run the code, capture output
    service = oatc.service
    action_id = oatc.action_id
    with io.StringIO() as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                _ = ii.runsource(source_code, symbol="exec")
        service.append_response_to_action(
            action_id,
            mime = "text/plain",
            text_content = f.getvalue(),
            user = user
        )

# Mermaid action handler
class SystemActionHandlerRequest(BaseModel):
    type: Literal["config", "mermaid", "html", "markdown", "python"]
    command_text: str
    args: str # string behind the verb(aka type)

class SystemActionHandler(ActionHandler):
    def parse_request(self, request:Any) -> Optional[SystemActionHandlerRequest]:
        try:
            parsed_request = SystemActionHandlerRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"SystemActionHandler.parse_request: invalid request format")
            return None       
        return parsed_request

    def cli_open(self, *args, **kwargs)->Union[BinaryIO, TextIO]:
        python_thread_context:PythonTheradContext = python_thread_context_var.get()
        user = python_thread_context.user
        filename = args[0]
        if filename.startswith("/"):
            raise ValueError(f"filename cannot start with /")
        new_args = [ os.path.join(self.config.core.users_home_dir, str(user.id), filename) ] + list(args[1:])
        return open(*new_args, **kwargs)


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        mermaid_request = self.parse_request(request)
        r = mermaid_request is not None
        logger.debug(f"SystemActionHandler.can_handler: {'Yes' if r else 'No'}")
        return r

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict) -> bool:
        log_prefix = "SystemActionHandler.handle"

        parsed_request = self.parse_request(request)
        if parsed_request is None:
            # This should never happen, since we will only call handle if we are able to parse the request
            logger.error(f"{log_prefix}: Unable to parse request, this should not happen, please investigate, request={request}, action_id={action_id}")
            return True
        
        match parsed_request.type:
            case "html":
                return self.handle_html(action_id, parsed_request, user, action_handler_user_config)
            case "markdown":
                return self.handle_markdown(action_id, parsed_request, user, action_handler_user_config)
            case "mermaid":
                return self.handle_mermaid(action_id, parsed_request, user, action_handler_user_config)
            case "config":
                return self.handle_config(action_id, parsed_request, user, action_handler_user_config)
            case "python":
                return self.handle_python(action_id, parsed_request, user, action_handler_user_config)
            case _:
                # This should never happen, if we are able to parse the request, type MUST be on of the above
                logger.error(f"{log_prefix}: Unable to parse request, invalid type: {parsed_request.type}, this should not happen, please investigate, request={request}, action_id={action_id}")
                return True

    def handle_html(self, action_id:int, parsed_request:SystemActionHandlerRequest, user:User, action_handler_user_config:dict) -> bool:
        self.service.append_response_to_action(
            action_id,
            mime = "text/html",
            text_content = parsed_request.command_text,
            user = user
        )
        logger.info(f"SystemActionHandler.handle_html: handled successfully, action_id={action_id}, user_id={user.id}")
        return True

    def handle_markdown(self, action_id:int, parsed_request:SystemActionHandlerRequest, user:User, action_handler_user_config:dict) -> bool:
        self.service.append_response_to_action(
            action_id,
            mime = "text/markdown",
            text_content = parsed_request.command_text,
            user = user
        )
        logger.info(f"SystemActionHandler.handle_markdown: handled successfully, action_id={action_id}, user_id={user.id}")
        return True

    def handle_mermaid(self, action_id:int, parsed_request:SystemActionHandlerRequest, user:User, action_handler_user_config:dict) -> bool:
        self.service.append_response_to_action(
            action_id,
            mime = "application/x-webcli-mermaid",
            text_content = parsed_request.command_text,
            user = user
        )
        logger.info(f"SystemActionHandler.handle_mermaid: handled successfully, action_id={action_id}, user_id={user.id}")
        return True

    def handle_config(self, action_id:int, parsed_request:SystemActionHandlerRequest, user:User, action_handler_user_config:dict) -> bool:
        log_prefix = "SystemActionHandler.handle_config"
        # parse args
        try:
            parser = argparse.ArgumentParser(description='', exit_on_error=False)
            parser.add_argument(
                "action_type", type=str, help="Specify action type",
                choices=['set', 'get'],
                nargs=1
            )
            parser.add_argument(
                "action_handler_name", type=str, help="Specify action handler name",
                nargs=1
            )
            args = parser.parse_args(shlex.split(parsed_request.args))
        except argparse.ArgumentError as e:
            logger.exception(f"{log_prefix}: handled failed, Invalid command line argument for %config%, args={parsed_request.args}, action_id={action_id}, user_id={user.id}")
            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = e.message,
                user = user
            )
            return True
        
        action_type = args.action_type[0]
        action_handler_name = args.action_handler_name[0]

        if action_type == "get":
            config = self.service.get_action_handler_user_config(
                action_handler_name = action_handler_name,
                user = user
            )

            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = json.dumps(config, indent=4),
                user = user
            )
            logger.info(f"{log_prefix}: handled successfully, action_id={action_id}, user_id={user.id}")
            return True
        
        if action_type == "set":
            try:
                json_content = json.loads(parsed_request.command_text)
            except json.decoder.JSONDecodeError:
                self.service.append_response_to_action(
                    action_id,
                    mime = "text/plain",
                    text_content = "config content MUST be JSON format, please retry!",
                    user = user
                )
                logger.exception(f"{log_prefix}: handled failed, action_id={action_id}, user_id={user.id}")
                return

            self.service.set_action_handler_user_config(
                action_handler_name = action_handler_name,
                user = user, 
                config = json_content
            )
            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = json.dumps(json_content, indent=4),
                user = user
            )
            logger.info(f"{log_prefix}: handled successfully, action_id={action_id}, user_id={user.id}")
            return True
        

    def handle_python(self, action_id:int, parsed_request:SystemActionHandlerRequest, user:User, action_handler_user_config:dict) -> bool:
        log_prefix = "SystemActionHandler.handle_python"
        try:
            parser = argparse.ArgumentParser(description='', exit_on_error=False)
            parser.add_argument("--load", type=str, required=False, help="load python file")
            parser.add_argument("--save", type=str, required=False, help="save python file")
            parser.add_argument("--print", action="store_true", help="print python file")
            args = parser.parse_args(shlex.split(parsed_request.args))
        except argparse.ArgumentError as e:
            logger.exception(f"{log_prefix}: handled failed, Invalid command line argument for %python%, args={parsed_request.args}, action_id={action_id}, user_id={user.id}")
            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = e.message,
                user = user
            )
            return True

        ######################################################################################
        # Usage:
        #
        # load your code in foo.py, prepend to your code and run it
        # %python% --load foo.py
        #
        # load your code in foo.py, print it, prepend to your code and run it
        # %python% --load foo.py --print
        #
        # save your code to foo.py and run it
        # %python% --save foo.py
        # 
        # Simply run your code
        # %python%
        ######################################################################################
        extra_code = ""
        if args.save is not None:
            user_home_dir = os.path.join(self.config.core.users_home_dir, str(user.id))
            os.makedirs(user_home_dir, exist_ok=True)
            filename = os.path.join(user_home_dir, args.save)
            with open(filename, "wt") as f:
                f.write(parsed_request.command_text)
        elif args.load is not None:
            user_home_dir = os.path.join(self.config.core.users_home_dir, str(user.id))
            os.makedirs(user_home_dir, exist_ok=True)
            filename = os.path.join(user_home_dir, args.load)
            try:
                with open(filename, "rt") as f:
                    extra_code = f.read()
            except FileNotFoundError:
                pass
            if args.print:
                self.service.append_response_to_action(
                    action_id,
                    mime = "text/plain",
                    text_content = extra_code,
                    user = user
                )

        oatc = PythonTheradContext(
            user = user,
            action_id = action_id,
            service = self.service
        )
        python_thread_context_var.set(oatc)

        run_code(
            oatc,
            {
                "cli_print": cli_print,
                "cli_open": self.cli_open,
            }, 
            parsed_request.command_text
        )
        return True
