from __future__ import annotations  # Enables forward declaration

from typing import Any, Optional
from abc import ABC, abstractmethod
from webcli2.core.data import User

class ActionHandler(ABC):
    require_shutdown: Optional[bool] = None
    service:Any = None

    # can you handle this request?
    @abstractmethod
    def can_handle(self, request:Any) -> bool:
        pass # pragma: no cover

    def startup(self, service:Any):
        # service is actually a webcli.core.service.WebCLIService
        assert self.require_shutdown is None
        assert self.service is None

        self.require_shutdown = False
        self.service = service

    def shutdown(self):
        # assert self.require_shutdown == False
        # assert self.cli_handler is not None

        # self.cli_handler = None
        # self.require_shutdown = None
        pass

    @abstractmethod
    def handle(self, action_id:int, request:Any, user:User, action_handler_user_config:dict) -> bool:
        ###################################################################################################
        # If return is True, it means the aciton is completed
        # If the return is False, it means the action is still pending, the action handler may queue
        # a taska and work on the action in the background
        ###################################################################################################

        # to complete the action, you can call
        # cli_handler.complete_action(None, action_id, ...)
        #
        # to update the action, you can call
        # cli_handler.update_action(None, action_id:int, ...):
        pass # pragma: no cover

    # An action handler can get other action handler by name
    def get_action_handler(self, action_handler_name:str) -> Optional["ActionHandler"]:
        return self.service.action_handlers.get(action_handler_name)

