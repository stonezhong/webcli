import os
import yaml
import logging
import logging.config        
import uvicorn

from webcli2.config import WebCLIApplicationConfig, load_config, normalize_filename

logger = None

class WebCLIApplication:
    webcli_home:str                     # WebCLI application home directory
    config_filename:str                 # WebCLI config file name, it is a YAML file
    config:WebCLIApplicationConfig      # config loaded from webcli_cfg.yaml
    
    def initialize_logging(self):
        # create loging directory
        os.makedirs(self.config.core.log_dir, exist_ok=True)

        # loading logging config
        if not os.path.isfile(self.config.core.log_config_filename):
            print(f"Missing log config file: {self.config.core.log_config_filename}")
            exit(1)
        with open(self.config.core.log_config_filename, "rt") as f:
            global logger
            log_config = yaml.safe_load(f)
        # patch filename field
        for _, handler_config in log_config.get("handlers", {}).items():
            if "filename" in handler_config:
                handler_config["filename"] = normalize_filename(
                    self.config.core.log_dir, 
                    handler_config["filename"]
                )
        logging.config.dictConfig(log_config)
        
        logger = logging.getLogger(__file__)
        logger.info("Logging is initialized")


    def initialize(self):
        self.config = load_config()
        if self.config is None:
            print(f"Missing config file")
            exit(1)

        self.initialize_logging()
        

    def start(self):
        self.initialize()
        from webcli2.web import app
        # run application
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)

def webcli():
    webcli_application = WebCLIApplication()
    webcli_application.start()

