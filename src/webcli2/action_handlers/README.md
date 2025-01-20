# Index
* [Client Action Handler](#client-action-handler)
    * [doAction](#doaction)
* [Server Action Handler](#server-action-handler)
* [Action Handlers](#action-handlers)
    * [Client](#client)
    * [server](#server)

# Client Action Handler
A client action handler is an object of javascript class `BaseActionHandler`.
Given a piece of user input text in `commandText`, if the handler can handle the text, `handler.getRequestFromCommandText(commandText)` should return a non-null object, or null, representing the handler cannot handle the object

## doAction
if the action handler has `doAction` method, this method will be called to trigger the action, otgherwise, the client will post an `aciton` to the server.

# Server Action Handler
A server action handler has two methods
* `can_handle`: this method tells if the action handler can handle the request or not
* `handle`: action handler handles the action in this method

Here is an example how you can register action in server
```python
manager = WebSocketConnectionManager()
cli_action_handler = PySparkActionHandler(
    stream_id = DEBUG_STREAM_ID,
    kafka_consumer_group_name = KAFKA_CONSUMER_GROUP_NAME,
    manager = manager
)
mermaid_action_handler = MermaidHandler(manager = manager)
cli_handler = CLIHandler(
    db_engine = engine, 
    debug=True, 
    action_handlers=[cli_action_handler, mermaid_action_handler]
)
```

## CLIHandler
This class handles client action request asynchronously. It rely on a list of action handlers to handler the client request

# Action Handlers
## Client
* [config](ConfigActionHandler.jsx)
* [pyspark](pyspark/README.md)
* [mermaid](mermaid/README.md)

## Server
* [pyspark](pyspark/README.md)
* [mermaid](mermaid/README.md)

