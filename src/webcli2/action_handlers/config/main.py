import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
import json

from pydantic import BaseModel, ValidationError

from webcli2 import ActionHandler
from pydantic import ValidationError
from webcli2.models import User

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
        logger.debug(f"{log_prefix}: enter")
        try:
            config_request = ConfigRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            logger.debug(f"{log_prefix}: exit")
            return None       
        logger.debug(f"{log_prefix}: exit")
        return config_request


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "ConfigHandler.can_handle"
        logger.debug(f"{log_prefix}: enter")
        config_request = self.parse_request(request)
        r = config_request is not None
        logger.debug(f"{log_prefix}: {'Yes' if r else 'No'}")
        logger.debug(f"{log_prefix}: exit")
        return r

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any, user:User):
        log_prefix = "ConfigHandler.handle"
        logger.debug(f"{log_prefix}: enter")

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
            logger.debug(f"{log_prefix}: exit")
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
            
            self.webcli_engine.complete_action(action_id, config_response.model_dump(mode="json"))
            self.webcli_engine.notify_websockt_client(
                config_request.client_id, 
                action_id, 
                config_response
            )
            logger.debug(f"{log_prefix}: exit")
            return

                

