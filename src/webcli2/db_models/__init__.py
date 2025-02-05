from sqlalchemy import Engine

from ._common import DBModelBase
from .main import DBAction, DBActionHandlerConfiguration, DBUser

def create_all_tables(engine:Engine):
    DBModelBase.metadata.create_all(engine)
