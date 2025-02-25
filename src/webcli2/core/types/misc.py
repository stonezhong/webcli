from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar("T")

class PatchValue(Generic[T], BaseModel):
    value: Optional[T] = None
