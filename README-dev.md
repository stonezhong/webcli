# Index
* [Classes](#classes)
    * [ActionHandlerManager](#actionhandlermanager)
# Classes
## WebCLIEngine
Purpose
* The core engine for web cli

Async Action Apis

| API    | Savings |
| -------- | ------- |
| `startup` | start up the engine |
| `shutdown` | shutdown the engine |
| `async_start_action` | It will find a proper action handler to handle the action, the action handler's `handle` method is called in manager's thread pool |
| `async_update_action` | Usually called by action handler to update an action progress |
| `async_complete_action` | Usually called by action handler to complete an action |
| `start_action` | sync version of `async_start_action` |
| `update_action` | sync version of `async_update_action` |
| `complete_action` | sync version of `async_complete_action` |
| `set_action_handler_configuration` | set action handler configuration |
| `get_action_handler_configuration` | get action handler configuration |
| `get_action_handler_configurations` | get configurations for all action handler |
