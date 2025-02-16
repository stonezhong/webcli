from __future__ import annotations

from typing import Optional
from sqlalchemy import Integer, Identity, String, ForeignKey, LargeBinary, Text, UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ._common import DBModelBase
from webcli2.webcli.output import MIMEType

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
class DBActionResponseChunk(DBModelBase):
    """
    Represent an async action response chunk
    """
    __tablename__ = 'async-action-response-chunks'

    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)
    action_id:  Mapped[int] = mapped_column(ForeignKey("async-actions.id"))
    order: Mapped[int] = mapped_column("order", Integer)
    mime: Mapped[MIMEType] = mapped_column("mime", Enum(MIMEType))
    text_content: Mapped[Optional[str]] = mapped_column("text_content", Text, nullable=True)
    binary_content: Mapped[Optional[bytes]] = mapped_column("binary_content", LargeBinary, nullable=True)

    __table_args__ = (
        UniqueConstraint('action_id', 'order', name='aarc_action_id_order'),
    )
