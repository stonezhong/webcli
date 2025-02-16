import enum
from pydantic import BaseModel

class MIMEType(enum.Enum):
    HTML                    = "text/html"
    JSON                    = "application/json"
    PNG                     = "image/png"
    MARKDOWN                = "text/markdown"
    TEXT                    = "text/plain"
    MERMAID                 = "application/webcli-mermaid"

class CLIOutputChunk(BaseModel):
    mime: MIMEType
    content: str
