# Index
* [Trigger an Action](#trigger-an-action)
* [Answer Panel](#answer-panel)
* [Tracking Actions](#tracking-actions)

# Trigger an Action

To trigger an action, you call the method `triggerAction(actionContext)`, `actionContext` is a JSON object.

* `triggerAction` is an async function
* It may handle it locally without a server round trip, for example, change local context.
* It may issue a REST API call, for example, send a command to spark server via the Web Server.


# Answer Panel
Each action, once triggered, upon completion, you will have a `actionResult` object. This `actionResult` object is an JSON object.
* `renderActionResult` method know how to render any action result into a react element, or null if you do not want to visualize the action result.

# Tracking Actions
Any action triggered will be tracked by a hashmap, key is action ID (integer), value is the action object

We have a web socket to receive action notification



