import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
import json

from pydantic import BaseModel, ValidationError

from webcli2 import ActionHandler
from pydantic import ValidationError
from webcli2.core.data import User
from webcli2.apilog import log_api_enter, log_api_exit

# Config action handler
class ConfigRequest(BaseModel):
    type: Literal["config"]
    client_id: str
    action: Literal['get', 'set']
    action_handler_name: str
    content: Optional[str]

class ConfigResponse(BaseModel):
    content: Optional[str]
    succeeded: bool
    error_message: Optional[str]

class ConfigHandler(ActionHandler):
    def parse_request(self, request:Any) -> Optional[ConfigRequest]:
        log_prefix = "ConfigHandler.parse_request"
        log_api_enter(logger, log_prefix)
        try:
            config_request = ConfigRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            log_api_exit(logger, log_prefix)
            return None       
        log_api_exit(logger, log_prefix)
        return config_request


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "ConfigHandler.can_handle"
        log_api_enter(logger, log_prefix)
        config_request = self.parse_request(request)
        r = config_request is not None
        logger.debug(f"{log_prefix}: {'Yes' if r else 'No'}")
        log_api_exit(logger, log_prefix)
        return r

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict) -> bool:
        log_prefix = "ConfigHandler.handle"
        log_api_enter(logger, log_prefix)

        config_request = self.parse_request(request)
        if config_request.action == "get":
            logger.debug(f"{log_prefix}: get config")
            config = self.service.get_action_handler_user_config(
                action_handler_name = config_request.action_handler_name,
                user = user
            )

            self.service.append_response_to_action(
                action_id,
                mime = "text/plain",
                text_content = json.dumps(config, indent=4),
                user = user
            )
            log_api_exit(logger, log_prefix)
            return True
        
        if config_request.action == "set":
            logger.debug(f"{log_prefix}: set config")
            try:
                json_content = json.loads(config_request.content)
                self.service.set_action_handler_user_config(
                    action_handler_name = config_request.action_handler_name,
                    user = user, 
                    config = json_content
                )
                self.service.append_response_to_action(
                    action_id,
                    mime = "text/plain",
                    text_content = json.dumps(json_content, indent=4),
                    user = user
                )
            except json.decoder.JSONDecodeError:
                self.service.append_response_to_action(
                    action_id,
                    mime = "text/plain",
                    text_content = "Config is not in JSON format",
                    user = user
                )
            logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
            log_api_exit(logger, log_prefix)
            return True
