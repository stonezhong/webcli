import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
from pydantic import BaseModel, ValidationError

from webcli2 import WebCLIEngine, ActionHandler
from pydantic import ValidationError
from webcli2.models import User

from openai import OpenAI

class OpenAIRequest(BaseModel):
    type: Literal["openai"]
    client_id: str
    command_text: str


class OpenAIResponse(BaseModel):
    message: str   # the message client need to display

class OpenAIActionHandler(ActionHandler):
    client: OpenAI

    def __init__(self):
        log_prefix = "OpenAIActionHandler.__init__"
        logger.debug(f"{log_prefix}: enter")
        self.client = OpenAI(api_key="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")
        logger.debug(f"{log_prefix}: exit")

    def startup(self, webcli_engine:WebCLIEngine):
        log_prefix = "OpenAIActionHandler.startup"
        logger.debug(f"{log_prefix}: enter")
        super().startup(webcli_engine)
        logger.debug(f"{log_prefix}: exit")

    def shutdown(self):
        log_prefix = "OpenAIActionHandler.shutdown"
        logger.debug(f"{log_prefix}: enter")
        assert self.require_shutdown == False
        assert self.webcli_engine is not None
        self.require_shutdown = True
        self.webcli_engine = None
        logger.debug(f"{log_prefix}: exit")


    def parse_request(self, request:Any) -> Optional[OpenAIRequest]:
        log_prefix = "OpenAIActionHandler.parse_request"
        logger.debug(f"{log_prefix}: exit")

        try:
            openai_request = OpenAIRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            logger.debug(f"{log_prefix}: exit")
            return None       
        logger.debug(f"{log_prefix}: exit")
        return openai_request

    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "OpenAIActionHandler.can_handle"
        logger.debug(f"{log_prefix}: enter")
        openai_request = self.parse_request(request)
        r = openai_request is not None
        logger.debug(f"{log_prefix}: exit")
        return r

    def handle(self, action_id:int, request:Any, user:User):
        log_prefix = "OpenAIActionHandler.handle"
        logger.debug(f"{log_prefix}: enter")

        openai_request = self.parse_request(request)
        completion = self.client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model="gpt-4",
            store=True,
            messages=[
                {"role": "user", "content": openai_request.command_text}
            ]
        )
        openai_response = OpenAIResponse(
            message = completion.choices[0].message.content
        )

        self.webcli_engine.complete_action(action_id, openai_response.model_dump(mode="json"))
        self.webcli_engine.notify_websockt_client(
            openai_request.client_id, 
            action_id, 
            openai_response
        )

        logger.debug(f"{log_prefix}: exit")
