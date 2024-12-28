from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, Identity, String, DateTime, func, Boolean, Enum, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ._common import DBModelBase

#############################################################################
# client create an async-action
# once created, is_completed is False
# before action is completed, client can update progress, every update
# will increase version
# until the action is completed, the version is going to update again
# the  initial version is always 0
#############################################################################
class DBAsyncAction(DBModelBase):
    """
    Represent an async action
    """
    __tablename__ = 'async-actions'

    # each job has a unique ID within the datalake
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    # is the action completed?
    is_completed: Mapped[bool] = mapped_column("is_completed", Boolean)

    # when the event is created
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime)

    # when the event is created
    completed_at: Mapped[Optional[datetime]] = mapped_column("completed_at", DateTime)

    # when the event is created
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)

    # request context
    request: Mapped[JSON] = mapped_column("request", JSON)

    # response context
    response: Mapped[Optional[JSON]] = mapped_column("response", JSON)

    # progresse context
    progress: Mapped[Optional[JSON]] = mapped_column("progress", JSON)

