from __future__ import annotations

from pydantic import BaseModel, Field
from webcli2.core.data.db_models import DBUser

class User(BaseModel):
    id: int
    is_active: bool
    email: str
    password_version: int = Field(exclude=True)
    password_hash: str = Field(exclude=True)

    @classmethod
    def from_db(cls, db_user:DBUser) -> "User":
        return User(
            id = db_user.id,
            is_active = db_user.is_active,
            email = db_user.email,
            password_version = db_user.password_version,
            password_hash = db_user.password_hash
        )
