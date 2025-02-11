from typing import Optional, Any, List, Union
import io
import enum
import code
from contextlib import redirect_stdout, redirect_stderr
import json

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


def run_code(locals:dict, source_code) -> CLIOutput:
    output = CLIOutput(chunks=[])
    def cli_print(content, mime:str=MIMEType.HTML, name:Optional[str]=None):
        do_cli_print(output, content, mime=mime, name=name)
    my_locals = locals.copy()
    my_locals.update({
        "cli_print": cli_print
    })
    ii = code.InteractiveInterpreter(locals=my_locals)

    # now run the code, capture output
    with io.StringIO() as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                _ = ii.runsource(source_code, symbol="exec")
        cli_print(f, mime=MIMEType.TEXT, name="stdout")
    
    return output
