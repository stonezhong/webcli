from __future__ import annotations

from sqlalchemy import Integer, Identity, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._common import DBModelBase
from . import db_action

class DBThreadAction(DBModelBase):
    """
    Represent a thread, action registry table
    """
    __tablename__ = 'DBThreadAction'

    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    thread_id:  Mapped[int] = mapped_column(ForeignKey("DBThread.id"))
    action_id:  Mapped[int] = mapped_column(ForeignKey("DBAction.id"))
    action:     Mapped[db_action.DBAction] = relationship(foreign_keys=[action_id])

    # within the thread, the display order of this action
    display_order: Mapped[int] = mapped_column("display_order", Integer)

    show_question: Mapped[bool] = mapped_column("show_question", Boolean)
    show_answer:   Mapped[bool] = mapped_column("show_answer", Boolean)

    __table_args__ = (
        UniqueConstraint('thread_id', 'action_id', name='threadaction_thread_id_action_id'),
    )
