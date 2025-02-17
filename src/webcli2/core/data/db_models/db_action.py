from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, Identity, String, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._common import DBModelBase
from . import db_user

#############################################################################
# Represent a DB layer action
# ---------------------------------------------------------------------------
# Once an action is created, is_completed is set to False
# Create an action:
#     It set is_completed to False, set request field
# Update an action:
#     It set the updated_at and progress field
# Complete an action:
#     It set is_completed to True, set response field
#############################################################################
class DBAction(DBModelBase):
    """
    Represent an async action
    """
    __tablename__ = 'DBAction'

    # each job has a unique ID within the datalake
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    # user who created this action
    user_id:  Mapped[int] = mapped_column(ForeignKey("DBUser.id"))
    user:     Mapped[db_user.DBUser] = relationship(foreign_keys=[user_id])

    # what is the name of the action handler that handles this action?
    handler_name: Mapped[str] = mapped_column("handler_name", String)

    # is the action completed?
    is_completed: Mapped[bool] = mapped_column("is_completed", Boolean)

    # when the event is created
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime)

    # when the event is created
    completed_at: Mapped[Optional[datetime]] = mapped_column("completed_at", DateTime)

    # request context, action handler's javascript parse the user input text and 
    # extract this request
    request: Mapped[JSON] = mapped_column("request", JSON)

    # title
    title: Mapped[str] = mapped_column("title", String)

    # the user input text
    raw_text: Mapped[str] = mapped_column("raw_text", Text)

