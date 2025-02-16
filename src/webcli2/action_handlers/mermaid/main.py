import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
from pydantic import BaseModel, ValidationError

from webcli2 import ActionHandler
from webcli2.models import User
from webcli2.apilog import log_api_enter, log_api_exit
from webcli2.webcli.output import MIMEType

# Mermaid action handler
class MermaidRequest(BaseModel):
    type: Literal["mermaid", "html", "markdown"]
    client_id: str
    command_text: str

class MermaidHandler(ActionHandler):
    def parse_request(self, request:Any) -> Optional[MermaidRequest]:
        try:
            mermaid_request = MermaidRequest.model_validate(request)
        except ValidationError:
            return None       
        return mermaid_request

    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        mermaid_request = self.parse_request(request)
        r = mermaid_request is not None
        logger.debug(f"MermaidHandler.can_handle: {'Yes' if r else 'No'}")
        return r


    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        try:
            self._handle(action_id, request, user, action_handler_user_config)
        except Exception:
            logger.exception("MermaidHandler.handle: failed to handle request")
            raise

    def _handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        mermaid_request = self.parse_request(request)

        # When this is called, browser is showing a spinning for the action
        if mermaid_request.type == "mermaid":
            mime = MIMEType.MERMAID
        elif mermaid_request.type == "html":
            mime = MIMEType.HTML
        elif mermaid_request.type == "markdown":
            mime = MIMEType.MARKDOWN

        self.webcli_engine.add_response_chunk(action_id, mime, mermaid_request.command_text, complete_action=True)
        logger.debug(f"MermaidHandler.handle: action has been handled successfully, action_id={action_id}")
