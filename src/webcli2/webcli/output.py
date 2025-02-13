from typing import Optional, Any, List
import enum
from pydantic import BaseModel

class MIMEType(enum.Enum):
    HTML                    = "text/html"
    JSON                    = "text/json"
    PNG                     = "image/png"
    MARKDOWN                = "text/markdown"
    TEXT                    = "text/plain"

class CLIOutputChunk(BaseModel):
    name: Optional[str] = None
    mime: MIMEType
    content: Any

class CLIOutput(BaseModel):
    chunks: List[CLIOutputChunk]
