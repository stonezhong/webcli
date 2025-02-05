from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, Identity, String, DateTime, func, Boolean, Enum, Index, JSON, \
    UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._common import DBModelBase

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
    __tablename__ = 'async-actions'

    # each job has a unique ID within the datalake
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    # user who created this action
    user_id:  Mapped[int] = mapped_column(ForeignKey("users.id"))
    user:     Mapped["DBUser"] = relationship(foreign_keys=[user_id])

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

#############################################################################
# Represent a DB layer action handler configuration
# ---------------------------------------------------------------------------
#############################################################################
class DBActionHandlerConfiguration(DBModelBase):
    """
    Represent an action configuration
    """
    __tablename__ = 'action-handler-configurations'

    # each configuration has a unique ID within the datalake
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    # which action handler this config is for
    action_handler_name: Mapped[str] = mapped_column("action_handler_name", String)

    user_id:  Mapped[int] = mapped_column(ForeignKey("users.id"))
    user:     Mapped["DBUser"] = relationship(foreign_keys=[user_id])

    # when the configuration is created
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime)

    # when the event is created
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)

    # request context
    configuration: Mapped[Optional[JSON]] = mapped_column("configuration", JSON)

    __table_args__ = (
        UniqueConstraint('action_handler_name', 'user_id', name='action_handler_user'),
    )

class DBUser(DBModelBase):
    """
    Represent a user
    """
    __tablename__ = 'users'

    # each cuser has a unique ID
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    is_active: Mapped[bool] = mapped_column("is_active", Boolean)
    email: Mapped[str] = mapped_column("email", String, unique=True)
    password_version: Mapped[int] = mapped_column("password_version", Integer)
    password_hash: Mapped[str] = mapped_column("password_hash", String)
