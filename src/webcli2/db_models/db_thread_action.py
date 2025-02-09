from sqlalchemy import Integer, Identity, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ._common import DBModelBase

class DBThreadAction(DBModelBase):
    """
    Represent a thread, action registry table
    """
    __tablename__ = 'thread-action-regs'

    id: Mapped[int] = mapped_column("id", Integer, Identity(start=1), primary_key=True)

    thread_id:  Mapped[int] = mapped_column(ForeignKey("threads.id"))
    action_id:  Mapped[int] = mapped_column(ForeignKey("async-actions.id"))
    action:     Mapped["DBAction"] = relationship(foreign_keys=[action_id])

    # within the thread, the display order of this action
    display_order: Mapped[int] = mapped_column("display_order", Integer)

    show_question: Mapped[bool] = mapped_column("show_question", Boolean)
    show_answer:   Mapped[bool] = mapped_column("show_answer", Boolean)

