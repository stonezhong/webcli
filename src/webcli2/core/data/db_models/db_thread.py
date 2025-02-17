from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, Identity, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._common import DBModelBase
from . import db_user

class DBThread(DBModelBase):
    """
    Represent a thread
    A thread contains bunch of actions around the same context
    """
    __tablename__ = 'DBThread'

    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    # user who created this action
    user_id:  Mapped[int] = mapped_column(ForeignKey("DBUser.id"))
    user:     Mapped[db_user.DBUser] = relationship(foreign_keys=[user_id])

    # when the thread is created
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime)

    title: Mapped[str] = mapped_column("title", String)
    description: Mapped[str] = mapped_column("description", String)

