from sqlalchemy import Engine

from ._common import DBModelBase
from .db_action import DBAction
from .db_action_handler_configuration import DBActionHandlerConfiguration
from .db_user import DBUser
from .db_thread import DBThread
from .db_thread_action import DBThreadAction
from .db_action_response_chunk import DBActionResponseChunk

def create_all_tables(engine:Engine):
    DBModelBase.metadata.create_all(engine)
