from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, Identity, String, Text, LargeBinary, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ._common import DBModelBase

#############################################################################
# Represent a DB layer action handler configuration
# ---------------------------------------------------------------------------
#############################################################################
class DBActionResponseChunk(DBModelBase):
    """
    Represent a chunk in action's response
    """
    __tablename__ = 'DBActionResponseChunk'

    # each configuration has a unique ID within the datalake
    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    action_id:  Mapped[int] = mapped_column(ForeignKey("DBAction.id"))
    order: Mapped[int] = mapped_column("order", Integer)

    mime: Mapped[str] = mapped_column("mime", String)

    text_content: Mapped[Optional[str]] = mapped_column("text_content", Text, nullable=True)
    binary_content: Mapped[Optional[bytes]] = mapped_column("binary_content", LargeBinary, nullable=True)

    __table_args__ = (
        UniqueConstraint('action_id', 'order', name='action_handler_user'),
    )

