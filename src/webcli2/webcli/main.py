from typing import Optional, Any, List, Union, Dict
import io
import enum
import threading
import code
from contextlib import redirect_stdout, redirect_stderr
import json
from webcli2.models import User

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

class UserPythonContext:
    ii: Optional[code.InteractiveInterpreter] = None
    stdout: Optional[CLIOutput] = None

GLOBAL_II_DICT: Dict[int, UserPythonContext] = {}
GLOBAL_II_DICT_LOCK = threading.Lock()

def do_cli_print(
    output:CLIOutput, 
    content:Union[str, bytes, io.StringIO, io.BytesIO, dict], 
    mime:str=MIMEType.HTML, 
    name:Optional[str]=None
):
    if isinstance(content, io.StringIO):
        actual_content = content.getvalue()
    elif isinstance(content, io.BytesIO):
        actual_content = content.getvalue()
    elif isinstance(content, bytes):
        actual_content = content
    elif isinstance(content, str):
        actual_content = content
    elif isinstance(content, dict):
        actual_content = json.dumps(content)

    else:
        raise ValueError(f"content has wrong type: {type(content)}")
    
    chunk = CLIOutputChunk(
        name = name,
        mime = mime,
        content=actual_content
    )
    output.chunks.append(chunk)


class CLIPrint:
    stdout: CLIOutput

    def __init__(self, stdout:CLIOutput):
        self.stdout = stdout

    def __call__(self, content, mime:str=MIMEType.HTML, name:Optional[str]=None):
        if isinstance(content, io.StringIO):
            actual_content = content.getvalue()
        elif isinstance(content, io.BytesIO):
            actual_content = content.getvalue()
        elif isinstance(content, bytes):
            actual_content = content
        elif isinstance(content, str):
            actual_content = content
        elif isinstance(content, dict):
            actual_content = json.dumps(content)
        else:
            raise ValueError(f"content has wrong type: {type(content)}")
        
        chunk = CLIOutputChunk(
            name = name,
            mime = mime,
            content=actual_content
        )
        self.stdout.chunks.append(chunk)


def run_code(user:User, locals:dict, source_code) -> CLIOutput:
    my_locals = locals.copy()
    with GLOBAL_II_DICT_LOCK:
        # we will create stdout if needed
        # we will create ii if needed
        if user.id not in GLOBAL_II_DICT:
            upc = UserPythonContext()
            GLOBAL_II_DICT[user.id] = upc
        else:
            upc = GLOBAL_II_DICT[user.id]
        
        if upc.stdout is None:
            upc.stdout = CLIOutput(chunks=[])
        
        if upc.ii is None:
            my_locals["cli_print"] = CLIPrint(upc.stdout)
            upc.ii = code.InteractiveInterpreter(locals=my_locals)
    
    # now run the code, capture output
    with io.StringIO() as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                _ = upc.ii.runsource(source_code, symbol="exec")
        upc.stdout.chunks.append(
            CLIOutputChunk(
                name = "stdout",
                mime = MIMEType.TEXT,
                content=f.getvalue()
            )
        )

def get_or_create_stdout(user:User):
    with GLOBAL_II_DICT_LOCK:
        # we will create stdout if needed
        if user.id not in GLOBAL_II_DICT:
            upc = UserPythonContext()
            GLOBAL_II_DICT[user.id] = upc
        else:
            upc = GLOBAL_II_DICT[user.id]
        
        if upc.stdout is None:
            upc.stdout = CLIOutput(chunks=[])
        
        return upc.stdout
        
