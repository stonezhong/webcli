from __future__ import annotations  # Enables forward declaration

from typing import Any, Optional
from abc import ABC, abstractmethod
import webcli2.webcli_engine as webcli_engine
from webcli2.models import User

class ActionHandler(ABC):
    webcli_engine: Optional[webcli_engine.WebCLIEngine] = None
    wsc_manager: Optional[webcli_engine.WebSocketConnectionManager] = None
    require_shutdown: Optional[bool] = None

    # can you handle this request?
    @abstractmethod
    def can_handle(self, request:Any) -> bool:
        pass # pragma: no cover

    def startup(self, webcli_engine:webcli_engine.WebCLIEngine):
        assert self.require_shutdown is None
        assert self.webcli_engine is None

        self.require_shutdown = False
        self.webcli_engine = webcli_engine

    def shutdown(self):
        # assert self.require_shutdown == False
        # assert self.cli_handler is not None

        # self.cli_handler = None
        # self.require_shutdown = None
        pass

    @abstractmethod
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict):
        # to complete the action, you can call
        # cli_handler.complete_action(None, action_id, ...)
        #
        # to update the action, you can call
        # cli_handler.update_action(None, action_id:int, ...):
        pass # pragma: no cover

    # An action handler can get other action handler by name
    def get_action_handler(self, action_handler_name:str) -> Optional["ActionHandler"]:
        return self.webcli_engine.action_handlers.get(action_handler_name)

