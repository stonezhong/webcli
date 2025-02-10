from typing import Optional

from ._common import CoreModelBase

class PatchThreadActionRequest(CoreModelBase):
    show_question: Optional[bool] = None
    show_answer: Optional[bool] = None

class PatchActionRequest(CoreModelBase):
    title: str

class CreateThreadRequest(CoreModelBase):
    title: str
    description: str

class CreateActionRequest(CoreModelBase):
    title: str
    raw_text: str
    request: dict

class PatchThreadRequest(CoreModelBase):
    title: Optional[str] = None
    description: Optional[str] = None
