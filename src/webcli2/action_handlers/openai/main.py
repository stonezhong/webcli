import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal, Union, Dict, BinaryIO, TextIO
import threading
import code
import os
import argparse
import shlex
import io
from contextvars import ContextVar
from contextlib import redirect_stdout, redirect_stderr

from pydantic import BaseModel, ValidationError

from webcli2.config import WebCLIApplicationConfig, load_config
from webcli2 import ActionHandler
from webcli2.core.data import User
from webcli2.apilog import log_api_enter, log_api_exit
from webcli2.core.ai import AIAgent, AITool

from openai import OpenAI

class OpenAITheradContext:
    user:User
    action_id:int
    service: Any

    def __init__(self, user:User, action_id:int, service:Any):
        self.user = user
        self.action_id = action_id
        self.service = service

openai_thread_context_var = ContextVar("openai_thread_context", default=None)

GLOBAL_II_DICT: Dict[int, code.InteractiveInterpreter] = {}
GLOBAL_II_DICT_LOCK = threading.Lock()

def run_code(oatc:OpenAITheradContext, locals:dict, source_code):
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


def cli_print(content:Union[str, bytes], *, mime:str="text/html"):
    openai_thread_context:OpenAITheradContext = openai_thread_context_var.get()
    service = openai_thread_context.service
    action_id = openai_thread_context.action_id
    user = openai_thread_context.user

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

######################################################################
# ArgumentParser.parse() failure causing application quit
# To workaround it, we need to re-define exit to avoid application 
# quit
######################################################################
class NoExitArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if message:
            raise ValueError(message)


class OpenAIRequest(BaseModel):
    type: Literal["openai", "python"]
    client_id: str
    command_text: str
    args: str

class OpenAIActionHandler(ActionHandler):
    config: WebCLIApplicationConfig

    def __init__(self):
        self.config = load_config()
        os.makedirs(self.config.core.resource_dir, exist_ok=True)

    def cli_open(self, *args, **kwargs)->Union[BinaryIO, TextIO]:
        openai_thread_context:OpenAITheradContext = openai_thread_context_var.get()
        user = openai_thread_context.user
        filename = args[0]
        if filename.startswith("/"):
            raise ValueError(f"filename cannot start with /")
        new_args = [ os.path.join(self.config.core.users_home_dir, str(user.id), filename) ] + list(args[1:])
        return open(*new_args, **kwargs)

    def create_ai_agent(self) -> AIAgent:
        openai_thread_context:OpenAITheradContext = openai_thread_context_var.get()
        user = openai_thread_context.user
        return AIAgent(self, user)

    def parse_request(self, request:Any) -> Optional[OpenAIRequest]:
        log_prefix = "OpenAIActionHandler.parse_request"
        log_api_enter(logger, log_prefix)

        try:
            openai_request = OpenAIRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            log_api_exit(logger, log_prefix)
            return None       
        log_api_exit(logger, log_prefix)
        return openai_request

    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "OpenAIActionHandler.can_handle"
        log_api_enter(logger, log_prefix)
        openai_request = self.parse_request(request)
        r = openai_request is not None
        log_api_exit(logger, log_prefix)
        return r

    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict) -> bool:
        try:
            return self._handle(action_id, request, user, action_handler_user_config)
        except Exception:
            logger.exception("OpenAIActionHandler.handle: failed to handle request")

    def handle_openai(
        self, 
        action_id:int, 
        openai_request:OpenAIRequest,
        user:User, 
        action_handler_user_config:dict,
        *,
        oatc:OpenAITheradContext
    ):
        # TODO: in case of exception, absorb the error and surface the error in openai_response
        log_prefix = "OpenAIActionHandler.handle_openai"

        api_key = action_handler_user_config.get("api_key")
        if not api_key:
            content = """
api_key must be provide, you can run 
%config% set openai
{
    "api_key": "YOUR_OPENAI_API_KEY_HERE"
}
"""
            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = content,
                user = user
            )
            return
        
        client = OpenAI(api_key=api_key)

        log_api_enter(logger, log_prefix)
        completion = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            # model="gpt-4",
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": openai_request.command_text}
            ]
        )
        self.service.append_response_to_action(
            action_id,
            mime = "text/markdown",
            text_content = completion.choices[0].message.content,
            user = user
        )
        
        log_api_exit(logger, log_prefix)
        return True

    def handle_python(
        self, 
        action_id:int, 
        openai_request:OpenAIRequest,
        user:User, 
        action_handler_user_config:dict,
        *,
        oatc:OpenAITheradContext
    ):
        # TODO: in case of exception, absorb the error and surface the error in openai_response
        log_prefix = "OpenAIActionHandler.handle_python"
        log_api_enter(logger, log_prefix)

        # parse args
        try:
            parser = NoExitArgumentParser(description='')
            parser.add_argument("--load", type=str, required=False, help="load python file")
            parser.add_argument("--save", type=str, required=False, help="save python file")
            parser.add_argument("--print", action="store_true", help="print python file")
            args = parser.parse_args(shlex.split(openai_request.args))
        except ValueError:
            logger.exception(f"{log_prefix}: %python% action has wrong arguments: {openai_request.args}, action_id={action_id}")
            args = None

        if args is not None and args.load is not None and args.save is not None:
            logger.warning(f"{log_prefix}: %python% action has wrong arguments: both load and save are set, action_id={action_id}")
            args = None
        
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
        if args is None:
            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = "wrong syntax",
                user = user
            )
            return

        extra_code = ""
        if args.save is not None:
            user_home_dir = os.path.join(self.config.core.users_home_dir, str(user.id))
            os.makedirs(user_home_dir, exist_ok=True)
            filename = os.path.join(user_home_dir, args.save)
            with open(filename, "wt") as f:
                f.write(openai_request.command_text)
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

        run_code(
            oatc,
            {
                "cli_print": cli_print,
                "cli_open": self.cli_open,
                "create_ai_agent": self.create_ai_agent
            }, 
            openai_request.command_text
        )
        log_api_exit(logger, log_prefix)
        return True

    def _handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        log_prefix = "OpenAIActionHandler.handle"
        log_api_enter(logger, log_prefix)

        oatc = OpenAITheradContext(
            user = user,
            action_id = action_id,
            service = self.service
        )
        openai_thread_context_var.set(oatc)

        openai_request = self.parse_request(request)

        if openai_request.type == "openai":
            ret = self.handle_openai(action_id, openai_request, user, action_handler_user_config, oatc=oatc)
        elif openai_request.type == "python":
            ret = self.handle_python(action_id, openai_request, user, action_handler_user_config, oatc=oatc)

        logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
        log_api_exit(logger, log_prefix)
        return ret
