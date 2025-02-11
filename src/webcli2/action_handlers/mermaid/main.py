import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
from base64 import b64encode, b64decode
from pydantic import BaseModel, ValidationError

from webcli2 import WebCLIEngine, ActionHandler
from pydantic import ValidationError
from webcli2.models import User
from webcli2.apilog import log_api_enter, log_api_exit

# Mermaid action handler
class MermaidRequest(BaseModel):
    type: Literal["mermaid", "html", "markdown"]
    client_id: str
    command_text: str

class MermaidResponse(BaseModel):
    type: Literal["mermaid", "html", "markdown"]
    content: str

class MermaidHandler(ActionHandler):
    def parse_request(self, request:Any) -> Optional[MermaidRequest]:
        log_prefix = "MermaidHandler.parse_request"
        log_api_enter(logger, log_prefix)
        try:
            mermaid_request = MermaidRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            log_api_exit(logger, log_prefix)
            return None       
        log_api_exit(logger, log_prefix)
        return mermaid_request


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "MermaidHandler.can_handle"
        log_api_enter(logger, log_prefix)
        mermaid_request = self.parse_request(request)
        r = mermaid_request is not None
        logger.debug(f"{log_prefix}: {'Yes' if r else 'No'}")
        log_api_exit(logger, log_prefix)
        return r

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any, user:User):
        log_prefix = "MermaidHandler.handle"
        log_api_enter(logger, log_prefix)

        mermaid_request = self.parse_request(request)
        mermaid_response = MermaidResponse(
            type=mermaid_request.type, 
            content = mermaid_request.command_text
        )
        logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
        self.webcli_engine.complete_action(action_id, mermaid_response.model_dump(mode="json"))
        self.webcli_engine.notify_websockt_client(
            mermaid_request.client_id, 
            action_id, 
            mermaid_response
        )
        log_api_exit(logger, log_prefix)
