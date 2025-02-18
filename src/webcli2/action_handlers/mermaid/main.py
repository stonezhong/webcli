from __future__ import annotations  # Enables forward declaration

import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
from pydantic import BaseModel, ValidationError

from webcli2 import ActionHandler
from pydantic import ValidationError
from webcli2.core.data import User

# Mermaid action handler
class MermaidRequest(BaseModel):
    type: Literal["mermaid", "html", "markdown"]
    client_id: str
    command_text: str

class MermaidHandler(ActionHandler):
    def parse_request(self, request:Any) -> Optional[MermaidRequest]:
        log_prefix = "MermaidHandler.parse_request"
        try:
            mermaid_request = MermaidRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            return None       
        return mermaid_request


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "MermaidHandler.can_handle"
        mermaid_request = self.parse_request(request)
        r = mermaid_request is not None
        logger.debug(f"{log_prefix}: {'Yes' if r else 'No'}")
        return r

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict) -> bool:
        log_prefix = "MermaidHandler.handle"

        mermaid_request = self.parse_request(request)
        if mermaid_request.type == "html":
            mime = "text/html"
        elif mermaid_request.type == "markdown":
            mime = "text/markdown"
        elif mermaid_request.type == "mermaid":
            mime = "application/x-webcli-mermaid"

        self.service.append_response_to_action(
            action_id,
            mime = mime,
            text_content = mermaid_request.command_text,
            user = user
        )
        logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
        return True
