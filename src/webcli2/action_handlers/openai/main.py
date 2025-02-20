import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
import os

from pydantic import BaseModel, ValidationError

from webcli2.config import WebCLIApplicationConfig, load_config
from webcli2 import ActionHandler
from webcli2.core.data import User
from webcli2.apilog import log_api_enter, log_api_exit
from webcli2.core.ai import AIAgent, AITool

from openai import OpenAI


class OpenAIRequest(BaseModel):
    type: Literal["openai"]
    client_id: str
    command_text: str

class OpenAIActionHandler(ActionHandler):
    config: WebCLIApplicationConfig

    def __init__(self):
        self.config = load_config()
        os.makedirs(self.config.core.resource_dir, exist_ok=True)


    # def create_ai_agent(self) -> AIAgent:
    #     openai_thread_context:OpenAITheradContext = openai_thread_context_var.get()
    #     user = openai_thread_context.user
    #     return AIAgent(self, user)

    def parse_request(self, request:Any) -> Optional[OpenAIRequest]:
        try:
            openai_request = OpenAIRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"OpenAIActionHandler.parse_request: invalid request format")
            return None       
        return openai_request

    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        openai_request = self.parse_request(request)
        r = openai_request is not None
        logger.debug(f"OpenAIActionHandler.can_handler: {'Yes' if r else 'No'}")
        return r

    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict) -> bool:
        # TODO: in case of exception, absorb the error and surface the error in openai_response
        log_prefix = "OpenAIActionHandler.handle"

        parsed_request = self.parse_request(request)
        if parsed_request is None:
            # This should never happen, since we will only call handle if we are able to parse the request
            logger.error(f"{log_prefix}: Unable to parse request, this should not happen, please investigate, request={request}, action_id={action_id}")
            return True


        api_key = action_handler_user_config.get("api_key")
        if not api_key:
            content = """
OpenAI api_key must be provide, you can run 
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
            logger.warning(f"OpenAIActionHandler.handle: unable to handle, client does not have OpenAI api_key, request={request}, action_id={action_id}")
            return True
        
        client = OpenAI(api_key=api_key)

        completion = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            # model="gpt-4",
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": parsed_request.command_text}
            ]
        )
        self.service.append_response_to_action(
            action_id,
            mime = "text/markdown",
            text_content = completion.choices[0].message.content,
            user = user
        )
        return True

