from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import Integer, Identity, String, DateTime, JSON, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._common import DBModelBase
from . import db_user

#############################################################################
# Represent a DB layer action handler configuration
# ---------------------------------------------------------------------------
#############################################################################
class DBActionHandlerConfiguration(DBModelBase):
    """
    Represent an action configuration
    """
    __tablename__ = 'DBActionHandlerConfiguration'

    # each configuration has a unique ID within the datalake
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    # which action handler this config is for
    action_handler_name: Mapped[str] = mapped_column("action_handler_name", String)

    user_id:  Mapped[int] = mapped_column(ForeignKey("DBUser.id"))
    user:     Mapped[db_user.DBUser] = relationship(foreign_keys=[user_id])

    # when the configuration is created
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime)

    # when the event is created
    updated_at: Mapped[Optional[datetime]] = mapped_column("updated_at", DateTime)

    # request context
    configuration: Mapped[Optional[JSON]] = mapped_column("configuration", JSON)

    __table_args__ = (
        UniqueConstraint('action_handler_name', 'user_id', name='action_handler_user'),
    )

