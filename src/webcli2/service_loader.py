import logging
logger = logging.getLogger(__name__)

from typing import Dict
import importlib

from sqlalchemy import create_engine

from webcli2.config import WebCLIApplicationConfig, ActionHandlerInfo
from webcli2.core.service import WebCLIService

# Load WebCLIService
def load_webcli_service(config:WebCLIApplicationConfig, ) -> WebCLIService:
    logger.info(f"load_webcli_service: Loading WebCLIService")
    action_handlers = { }

    action_handlers_config:Dict[str, ActionHandlerInfo] = {
        "config": ActionHandlerInfo(
            module_name="webcli2.action_handlers.system",
            class_name="SystemActionHandler",
            config = {}
        )
    }
    action_handlers_config.update(config.core.action_handlers)
    for action_handler_name, action_handler_info in action_handlers_config.items():
        logger.info(f"Loading action handler: name={action_handler_name}, module={action_handler_info.module_name}, class={action_handler_info.class_name}")
        module = importlib.import_module(action_handler_info.module_name)
        klass = getattr(module, action_handler_info.class_name)
        action_handler = klass(**action_handler_info.config)
        action_handlers[action_handler_name] = action_handler
    logger.info(f"All action handlers are loaded")

    db_engine = create_engine(config.core.db_url)

    service = WebCLIService(
        users_home_dir = config.core.users_home_dir,
        resource_dir = config.core.resource_dir,
        public_key=config.core.public_key,
        private_key=config.core.private_key,
        db_engine=db_engine,
        action_handlers = action_handlers
    )
    logger.info(f"load_webcli_service: WebCLIService is loaded!")
    return service
