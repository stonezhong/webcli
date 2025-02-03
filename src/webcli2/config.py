from typing import Optional, Dict

import os
from pydantic import BaseModel
import yaml

#############################################################################
# This model defines WebCLI Application config
#############################################################################
class WebCLIApplicationConfig(BaseModel):
    core: "CoreConfig"

class CoreConfig(BaseModel):
    home_dir:str = ""           # home directory
    log_config_filename: str = "logcfg.yaml"
    log_dir: str = "logs"       # a directory to store log files
    websocket_uri:str           # client must provide web socket uri, e.g. ws://localhost:8000/ws
    db_url:str
    action_handlers: Dict[str, "ActionHandlerInfo"] = {}

class ActionHandlerInfo(BaseModel):
    module_name: str
    class_name: str
    config: dict = {}
    
def normalize_filename(base_dir:str, filename:str):
    filename = os.path.expanduser(filename)
    filename = os.path.expandvars(filename)
    return filename if filename.startswith("/") else os.path.join(base_dir, filename)

def load_config() ->Optional[WebCLIApplicationConfig]:
    webcli_home = os.environ.get("WEBCLI_HOME") or os.path.expanduser("~/webcli")
    config_filename = os.path.join(webcli_home, "webcli_cfg.yaml")

    if not os.path.isfile(config_filename):
        return None

    with open(config_filename, "rt") as f:
        conifg_json = yaml.safe_load(f)
        config = WebCLIApplicationConfig.model_validate(conifg_json)
    
    # patch the config if needed
    config.core.home_dir = webcli_home

    config.core.log_dir = normalize_filename(webcli_home, config.core.log_dir)
    config.core.log_config_filename = normalize_filename(webcli_home, config.core.log_config_filename)
    
    return config
