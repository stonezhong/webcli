import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal, List, Dict, TextIO, BinaryIO, Union
from pydantic import BaseModel, ValidationError
import uuid
import os
import argparse
import shlex
import code

from webcli2.config import WebCLIApplicationConfig, load_config
from webcli2 import WebCLIEngine, ActionHandler
from pydantic import ValidationError
from webcli2.models import User
from webcli2.webcli import MIMEType, run_code, get_or_create_stdout, CLIOutput, CLIPrint, CLIOutputChunk
from oracle_spark_tools.cli import CommandType
from webcli2.apilog import log_api_enter, log_api_exit

from openai import OpenAI

######################################################################
# ArgumentParser.parse() failure causing application quit
# To workaround it, we need to re-define exit to avoid application 
# quit
######################################################################
class NoExitArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if message:
            raise ValueError(message)

######################################################################
# TODO: look for function feature in openai API, probably
#       no need to parse the openai output
######################################################################
def extract_code(content:str, text_type:str):
    ret = []
    p = 0
    while True:
        bp = content.find(f"```{text_type}", p)
        if bp < 0:
            return ret
        ep = content.find("```", bp+3)
        if ep < 0:
            return ret
        ret.append(content[bp+3+len(text_type):ep])
        p = ep+3


class OpenAIRequest(BaseModel):
    type: Literal["openai", "python"]
    client_id: str
    command_text: str
    args: str

class OpenAIResponse(BaseModel):
    stdout: CLIOutput

def render_response(response:CLIOutput, action_id:int, resource_dir:str):
    for chunk in response.chunks:
        if chunk.mime == MIMEType.PNG:
            fname = f"{str(uuid.uuid4())}.png"
            resource_dir = os.path.join(resource_dir, str(action_id))
            os.makedirs(resource_dir, exist_ok=True)
            # write to resource file
            with open(os.path.join(resource_dir, fname), "wb") as resource_f:
                resource_f.write(chunk.content)
            chunk.content = f"<img src='/resources/{str(action_id)}/{fname}' />"


class OpenAIActionHandler(ActionHandler):
    client: OpenAI
    config: WebCLIApplicationConfig

    def __init__(self, *, api_key:str):
        self.client = OpenAI(api_key=api_key)
        self.config = load_config()
        os.makedirs(self.config.core.resource_dir, exist_ok=True)

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

    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        try:
            self._handle(action_id, request, user, action_handler_user_config)
        except Exception:
            logger.exception("OpenAIActionHandler.handle: failed to handle request")

    def handle_openai(
        self, 
        action_id:int, 
        openai_request:OpenAIRequest,
        user:User, 
        action_handler_user_config:dict
    ) -> OpenAIResponse:
        # TODO: in case of exception, absorb the error and surface the error in openai_response
        log_prefix = "OpenAIActionHandler.handle_openai"
        log_api_enter(logger, log_prefix)
        completion = self.client.chat.completions.create(
            # model="gpt-3.5-turbo",
            # model="gpt-4",
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": openai_request.command_text}
            ]
        )
        openai_response = OpenAIResponse(
            stdout=CLIOutput(
                chunks=[
                    CLIOutputChunk(
                        mime = MIMEType.MARKDOWN,
                        content = completion.choices[0].message.content
                    )
                ]
            )
        )
        log_api_exit(logger, log_prefix)
        return openai_response

    def handle_python(
        self, 
        action_id:int, 
        openai_request:OpenAIRequest,
        user:User, 
        action_handler_user_config:dict
    ) -> OpenAIResponse:
        # TODO: in case of exception, absorb the error and surface the error in openai_response
        log_prefix = "OpenAIActionHandler.handle_python"
        log_api_enter(logger, log_prefix)

        stdout = get_or_create_stdout(user)
        cli_print = CLIPrint(stdout)
        openai_response = OpenAIResponse(stdout=CLIOutput(chunks=[]))

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
        
        if args is None:
            cli_print("wrong arguments for %python% action", mime=MIMEType.TEXT)
            openai_response.stdout.chunks = stdout.chunks.copy()
            stdout.chunks.clear()
            log_api_exit(logger, log_prefix)
            return openai_response
        
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
                cli_print(extra_code, mime=MIMEType.TEXT)

        pyspark_handler = self.get_action_handler("pyspark")
        def cli_open(*args, **kwargs)->Union[BinaryIO, TextIO]:
            filename = args[0]
            if filename.startswith("/"):
                raise ValueError(f"filename cannot start with /")
            new_args = [ os.path.join(self.config.core.users_home_dir, str(user.id), filename) ] + args[1:]
            return open(*new_args, **kwargs)
        def run_pyspark_python(source_code:str) -> str:
            return pyspark_handler.run_pyspark_code(
                user = user,
                client_id = openai_request.client_id, 
                command_type = CommandType.PYTHON, 
                source_code = source_code
            )
        def run_pyspark_bash(source_code:str) -> str:
            return pyspark_handler.run_pyspark_code(
                user = user,
                client_id = openai_request.client_id, 
                command_type = CommandType.BASH, 
                source_code = source_code
            )
        def run_pyspark_sql(sql_query:str) -> str:
            source_code = f"spark.sql({repr(sql_query)}).show()"
            return pyspark_handler.run_pyspark_code(
                user = user,
                client_id = openai_request.client_id, 
                command_type = CommandType.PYTHON, 
                source_code = source_code
            )
        def openai(question:str):
            completion = self.client.chat.completions.create(
                # model="gpt-3.5-turbo",
                # model="gpt-4",
                model="gpt-4o",
                store=True,
                messages=[
                    {"role": "user", "content": question}
                ]
            )
            return completion.choices[0].message.content

        run_code(
            user,
            {
                "run_pyspark_python": run_pyspark_python,
                "run_pyspark_bash": run_pyspark_bash,
                "run_pyspark_sql": run_pyspark_sql,
                "openai": openai,
                "extract_code": extract_code,
                "cli_open": cli_open
            }, 
            extra_code + "\n" + openai_request.command_text
        )

        openai_response.stdout.chunks = stdout.chunks.copy()
        stdout.chunks.clear()
        render_response(openai_response.stdout, action_id, self.config.core.resource_dir)
        log_api_exit(logger, log_prefix)
        return openai_response

    def _handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        log_prefix = "OpenAIActionHandler.handle"
        log_api_enter(logger, log_prefix)

        openai_request = self.parse_request(request)
        if openai_request.type == "openai":
            openai_response = self.handle_openai(action_id, openai_request, user, action_handler_user_config)
        elif openai_request.type == "python":
            openai_response = self.handle_python(action_id, openai_request, user, action_handler_user_config)

        logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
        self.webcli_engine.complete_action(action_id, openai_response.model_dump(mode="json"))
        self.webcli_engine.notify_websockt_client(
            openai_request.client_id, 
            action_id, 
            openai_response
        )

        log_api_exit(logger, log_prefix)
