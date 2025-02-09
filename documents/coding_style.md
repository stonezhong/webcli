# Index
* [Python](#python)

# Python
* See also [Google Python Style Guide](#https://google.github.io/styleguide/pyguide.html)

## Something to hightlight:
### Import
Please follow the order below:
* import python system variables, classes, etc (those are distributed with python itself, does not require pip install)
* import 3rd party variables, classes, etc. (those are installed via pip)
* import application variables, classes, etc (those are implemented within this application)
### Always annotate variables, functions, etc
### Try to now expose too many global variables
Here is an example:
```python
action_handlers = {
}

def config_action_handlers():
    action_handlers_config:Dict[str, ActionHandlerInfo] = {
        "config": ActionHandlerInfo(
            module_name="webcli2.action_handlers.config",
            class_name="ConfigHandler",
            config = {}
        )
    }
    action_handlers_config.update(config.core.action_handlers)
    for action_handler_name, action_handler_info in action_handlers_config.items():
        logger.info(f"Loading action handler: name={action_handler_name}, module={action_handler_info.module_name}, class={action_handler_info.class_name}")
        module = importlib.import_module(action_handler_info.module_name)
        klass = getattr(module, action_handler_info.class_name)
        action_handler = klass(**action_handler_info.config)
        action_handlers[action_handler_name] = action_handler
config_action_handlers()
```
This way, we can move `action_handlers_config` to inside a function and do not pollute global spaces.
### Always initialize logger at top
For eample, always put the following code at the very begining of your python file.
```python
import logging
logger = logging.getLogger(__name__)
...
```