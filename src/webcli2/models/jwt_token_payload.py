from ._common import CoreModelBase

class JWTTokenPayload(CoreModelBase):
    email: str
    password_version: int
    sub: str
    uuid: str

