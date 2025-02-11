import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal, List
from pydantic import BaseModel, ValidationError
import uuid
import os
import json

from webcli2.config import WebCLIApplicationConfig, load_config
from webcli2 import WebCLIEngine, ActionHandler
from pydantic import ValidationError
from webcli2.models import User
from webcli2.webcli import MIMEType, run_code
from oracle_spark_tools.cli import CommandType
from webcli2.apilog import log_api_enter, log_api_exit

from openai import OpenAI

class OpenAIRequest(BaseModel):
    type: Literal["openai", "python"]
    client_id: str
    command_text: str

class OpenAIResponseChunk(BaseModel):
    mime: MIMEType
    content: str

class OpenAIResponse(BaseModel):
    chunks: List[OpenAIResponseChunk]

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

    def handle(self, action_id:int, request:Any, user:User):
        log_prefix = "OpenAIActionHandler.handle"
        log_api_enter(logger, log_prefix)

        openai_request = self.parse_request(request)
        if openai_request.type == "openai":
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
                chunks=[
                    OpenAIResponseChunk(
                        mime = MIMEType.MARKDOWN,
                        content = completion.choices[0].message.content
                    )
                ]
            )
        elif openai_request.type == "python":
            pyspark_handler = self.get_action_handler("pyspark")
            def run_pyspark_python(*, server_id:str, source_code:str) -> str:
                return pyspark_handler.run_pyspark_code(
                    server_id=server_id, 
                    client_id = openai_request.client_id, 
                    command_type = CommandType.PYTHON, 
                    source_code = source_code
                )
            def run_pyspark_bash(*, server_id:str, source_code:str) -> str:
                return pyspark_handler.run_pyspark_code(
                    server_id=server_id, 
                    client_id = openai_request.client_id, 
                    command_type = CommandType.BASH, 
                    source_code = source_code
                )
            try:
                output = run_code(
                    {
                        "run_pyspark_python": run_pyspark_python,
                        "run_pyspark_bash": run_pyspark_bash,
                    }, 
                    openai_request.command_text
                )
            except Exception as e:
                logger.exception("unable to run the code")
                raise

            # marshal the output
            openai_response = OpenAIResponse(chunks=[])
            try:
                for chunk in output.chunks:
                    if chunk.mime == MIMEType.PNG:
                        fname = f"{str(uuid.uuid4())}.png"
                        resource_dir = os.path.join(self.config.core.resource_dir, str(action_id))
                        os.makedirs(resource_dir, exist_ok=True)
                        # write to resource file
                        with open(os.path.join(resource_dir, fname), "wb") as resource_f:
                            resource_f.write(chunk.content)
                        openai_response_chunk = OpenAIResponseChunk(
                            mime = chunk.mime,
                            content=f"<img src='/resources/{str(action_id)}/{fname}' />"
                        )
                    else:
                        openai_response_chunk = OpenAIResponseChunk(
                            mime = chunk.mime,
                            content=chunk.content
                        )
                    openai_response.chunks.append(openai_response_chunk)
            except Exception as e:
                logger.exception("unable to marshal output")
                raise

        logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
        self.webcli_engine.complete_action(action_id, openai_response.model_dump(mode="json"))
        self.webcli_engine.notify_websockt_client(
            openai_request.client_id, 
            action_id, 
            openai_response
        )

        log_api_exit(logger, log_prefix)
