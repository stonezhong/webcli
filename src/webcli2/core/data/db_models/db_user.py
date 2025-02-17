from __future__ import annotations

from sqlalchemy import Integer, Identity, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ._common import DBModelBase

class DBUser(DBModelBase):
    """
    Represent a user
    """
    __tablename__ = 'DBUser'

    # each cuser has a unique ID
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    is_active: Mapped[bool] = mapped_column("is_active", Boolean)
    email: Mapped[str] = mapped_column("email", String, unique=True)
    password_version: Mapped[int] = mapped_column("password_version", Integer)
    password_hash: Mapped[str] = mapped_column("password_hash", String)

