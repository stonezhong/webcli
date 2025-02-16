import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
import json

from pydantic import BaseModel, ValidationError

from webcli2 import ActionHandler
from pydantic import ValidationError
from webcli2.models import User
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
        try:
            config_request = ConfigRequest.model_validate(request)
        except ValidationError:
            return None       
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
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        log_prefix = "ConfigHandler.handle"
        log_api_enter(logger, log_prefix)

        config_request = self.parse_request(request)
        if config_request.action == "get":
            logger.debug(f"{log_prefix}: get config")
            ahc = self.webcli_engine.get_action_handler_configuration(
                config_request.action_handler_name,
                user.id
            )
            if ahc is None:
                config_response = ConfigResponse(
                    content=None,
                    succeeded=False,
                    error_message = f"config for \"{config_request.action_handler_name}\" does not exist"
                )
            else:
                config_response = ConfigResponse(
                    content=json.dumps(ahc.configuration, indent=4),
                    succeeded=True,
                    error_message = None
                )
            self.webcli_engine.complete_action(action_id, config_response.model_dump(mode="json"))
            self.webcli_engine.notify_websockt_client(
                config_request.client_id, 
                action_id, 
                config_response
            )
            log_api_exit(logger, log_prefix)
            return
        
        if config_request.action == "set":
            logger.debug(f"{log_prefix}: set config")
            try:
                json_content = json.loads(config_request.content)
                ahc = self.webcli_engine.set_action_handler_configuration(
                    config_request.action_handler_name,
                    user.id,
                    json_content
                )
                config_response = ConfigResponse(
                    content=json.dumps(ahc.configuration, indent=4),
                    succeeded=True, 
                    error_message = None
                )
            except json.decoder.JSONDecodeError:
                config_response = ConfigResponse(
                    content=None,
                    succeeded=False,
                    error_message = f"config should be JSON string"
                )
            
            logger.debug(f"{log_prefix}: action has been handled successfully, action_id={action_id}")
            self.webcli_engine.complete_action(action_id, config_response.model_dump(mode="json"))
            self.webcli_engine.notify_websockt_client(
                config_request.client_id, 
                action_id, 
                config_response
            )
            log_api_exit(logger, log_prefix)
            return
