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
    private_key: str            # for generating JWT token
    public_key: str             # for verifying JWT token
    resource_dir:str            
    users_home_dir:str

#################################################
# resource_dir
#
# When server send response to client, it support binary format, for example images, etc
# We will generate binary file here and change the output to points to here
#################################################

#################################################
# users_home_dir
#
# This is the parent directory for all user home directory
# use's home directory is
# {config.core.users_home_dir}/{user.id}
#
#################################################

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

    config.core.resource_dir = normalize_filename(webcli_home, config.core.resource_dir)
    config.core.users_home_dir = normalize_filename(webcli_home, config.core.users_home_dir)
    config.core.log_dir = normalize_filename(webcli_home, config.core.log_dir)
    config.core.log_config_filename = normalize_filename(webcli_home, config.core.log_config_filename)
    
    return config
