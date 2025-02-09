from typing import Optional
from datetime import datetime

from ._common import CoreModelBase
from webcli2.db_models import DBActionHandlerConfiguration

class ActionHandlerConfiguration(CoreModelBase):
    id: int
    action_handler_name: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    configuration: Optional[dict]

    @classmethod
    def create(self, db_ahc:DBActionHandlerConfiguration) -> "ActionHandlerConfiguration":
        return ActionHandlerConfiguration(
            id = db_ahc.id,
            action_handler_name = db_ahc.action_handler_name,
            user_id = db_ahc.user_id,
            created_at = db_ahc.created_at,
            updated_at = db_ahc.updated_at,
            configuration = db_ahc.configuration
        )

