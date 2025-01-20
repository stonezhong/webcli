import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
from base64 import b64encode, b64decode
from pydantic import BaseModel, ValidationError
import os
import tempfile
import asyncio

from webcli2 import WebCLIEngine, ActionHandler
from pydantic import ValidationError

import mermaid as md
from mermaid.graph import Graph


from webcli2.websocket import WebSocketConnectionManager

# Mermaid action handler
class MermaidRequest(BaseModel):
    type: Literal["mermaid"]
    client_id: str
    command_text: str

class MermaidResponse(BaseModel):
    type: Literal["mermaid"]
    svg: str

class MermaidHandler(ActionHandler):
    def __init__(self):
        log_prefix = "MermaidHandler.__init__"
        logger.debug(f"{log_prefix}: enter")
        logger.debug(f"{log_prefix}: exit")

    def startup(self, webcli_engine:WebCLIEngine):
        log_prefix = "MermaidHandler.startup"
        logger.debug(f"{log_prefix}: enter")
        super().startup(webcli_engine)
        logger.debug(f"{log_prefix}: exit")

    def shutdown(self):
        log_prefix = "MermaidHandler.shutdown"
        logger.debug(f"{log_prefix}: enter")
        assert self.require_shutdown == False
        assert self.webcli_engine is not None
        self.require_shutdown = True
        self.webcli_engine = None
        logger.debug(f"{log_prefix}: exit")

    def parse_request(self, request:Any) -> Optional[MermaidRequest]:
        log_prefix = "MermaidHandler.parse_request"
        logger.debug(f"{log_prefix}: enter")
        try:
            mermaid_request = MermaidRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            logger.debug(f"{log_prefix}: exit")
            return None       
        logger.debug(f"{log_prefix}: exit")
        return mermaid_request


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "MermaidHandler.can_handle"
        logger.debug(f"{log_prefix}: enter")
        mermaid_request = self.parse_request(request)
        r = mermaid_request is not None
        logger.debug(f"{log_prefix}: {'Yes' if r else 'No'}")
        logger.debug(f"{log_prefix}: exit")
        return r

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any):
        log_prefix = "MermaidHandler.can_handle"
        logger.debug(f"{log_prefix}: enter")
        # TODO: if we are not able to send message, we should complete the action, set error code
        f = None
        try:
            f = tempfile.NamedTemporaryFile(mode="w", suffix=".svg")
            f.close()
            mermaid_request = self.parse_request(request)
            lines = mermaid_request.command_text.split("\n")
            graph = Graph('no title',"\n".join(lines[1:]))
            render = md.Mermaid(graph)
            render.to_svg(f.name)

            with open(f.name, "rt") as ff:
                svg = ff.read()
            mermaid_response = MermaidResponse(type="mermaid", svg = svg)
            self.webcli_engine.complete_action(action_id, mermaid_response.model_dump(mode="json"))
            self.webcli_engine.notify_websockt_client(
                mermaid_request.client_id, 
                action_id, 
                mermaid_response
            )
            logger.debug(f"{log_prefix}: exit")
        except:
            logger.debug(f"{log_prefix}: exception captured", exc_info=True)
        finally:
            if f is not None and os.path.isfile(f.name):
                os.remove(f.name)
