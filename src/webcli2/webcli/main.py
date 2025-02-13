from typing import Dict
import io
import threading
import code
from contextlib import redirect_stdout, redirect_stderr
from webcli2.models import User
from .output import CLIOutput, MIMEType, CLIOutputChunk
from webcli2.webcli_engine import TheradContext

GLOBAL_II_DICT: Dict[int, code.InteractiveInterpreter] = {}
GLOBAL_II_DICT_LOCK = threading.Lock()

def run_code(tc:TheradContext, user:User, client_id:str, locals:dict, source_code) -> CLIOutput:
    my_locals = locals.copy()

    safe_user = User(id=user.id, is_active=user.is_active, email=user.email, password_version=1, password_hash="***")
    def current_user() -> User:
        # retrun safe_user since we do not want to leak password hash to client
        return safe_user
    my_locals["current_user"] = current_user

    with GLOBAL_II_DICT_LOCK:
        # we will create stdout if needed
        # we will create ii if needed
        if user.id not in GLOBAL_II_DICT:
            ii = code.InteractiveInterpreter(locals=my_locals)
            GLOBAL_II_DICT[user.id] = ii
        else:
            ii = GLOBAL_II_DICT[user.id]
    
    # now run the code, capture output
    with io.StringIO() as f:
        with redirect_stdout(f):
            with redirect_stderr(f):
                _ = ii.runsource(source_code, symbol="exec")
        tc.stdout.chunks.append(
            CLIOutputChunk(
                name = "stdout",
                mime = MIMEType.TEXT,
                content=f.getvalue()
            )
        )
