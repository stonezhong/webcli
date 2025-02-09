from typing import Optional
import os
import logging.config
import yaml
from webcli2.config import load_config, WebCLIApplicationConfig, normalize_filename

#############################################################
# This module do the following
# - load config
# - initialize logging
# then pass contrl to webcli_internal
#############################################################

def webcli():
    config:Optional[WebCLIApplicationConfig] = load_config()
    if config is None:
        print(f"Missing config file")
        exit(1)
    
    # create log directory, ok if the log directory is already there
    os.makedirs(config.core.log_dir, exist_ok=True)

    # loading logging config
    if not os.path.isfile(config.core.log_config_filename):
        print(f"Missing log config file: {config.core.log_config_filename}")
        exit(1)

    with open(config.core.log_config_filename, "rt") as f:
        log_config = yaml.safe_load(f)

    # patch the log config
    for _, handler_config in log_config.get("handlers", {}).items():
        if "filename" in handler_config:
            handler_config["filename"] = normalize_filename(
                config.core.log_dir, 
                handler_config["filename"]
            )
    logging.config.dictConfig(log_config)
    logger = logging.getLogger(__name__)
    logger.info("Logging is initialized")

    from .main_internal import webcli_internal
    webcli_internal(config, log_config)
