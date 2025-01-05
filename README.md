# Index
* [Concepts](#concepts)
    * [Action](#action)
* [APIs](#apis)
    * [ActionHandler](#actionhandler)
    * [CLIHandler](#clihandler)
* [Action Handlers](#action-handlers)
    * [CLIActionHandler](#cliactionhandler)
    * [MermaidHandler](#mermaidhandler)

# Concepts
## Action

Represent an action:
* When an action is created, request field stores the context on what is action is about. It is a JSON object.
* When an action is completed -- either successfully or failed, the response field store the action result. It is a JSON object
* Once an action is created, before it is completed, you can update the progress information, it is stored in progress field. It is a JSON field.

# APIs
## ActionHandler
* The <code>can_handler</code> method tells if a handler can handle an action or not
* The <code>handle</code> method actually handles the action

## CLIHandler
<table>
    <tr><th>Name</th><th>Async</th><th>Description</th></tr>
    <tr>
        <td><code>async_start_action</code></td><td>YES</td>
        <td>
            Create an action. It returns a tuple of status and action being created.
            If action is created successfully, status will be <code>CLIHandlerStatus.OK</code>, and the newly created action will be returned, the returned action has already been saved to database.<br /><br />
            CLIHandler will find the first action handler which can handle the action to handler it, or it will fail with <code>NO_HANDLER</code>.<br /><br />
            Once an action is created, the handler's <code>handle</code> method has been scheduled in a threadpool. The action handler's <code>handle</code> method is suppose to take care of the execution of the action<br/><br/>
            Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The action has been created, the Action object is returned. The customer action handler's <code>handle</code> method has been scheduled in a thread pool</td>
</tr>
<tr>
<td>SHUTDOWN_IN_PROGRESS</td>
<td>This means the CLIHandler is in the progress of shutdown and does not serve creating new actions.</td>
</tr>
<tr>
<td>NO_HANDLER</td>
<td>Cannot find a handler that can handle this action. You need to make sure when you create CLIHandler, <code>action_handlers</code> is set properly</td>
</tr>
</tr>
<tr>
<td>DB_FAILED</td>
<td>Cannot save the action to database, probably check your DB configuration and connectivity</td>
</tr>
<br/>
</table>
        </td>
    </tr>
    <tr>
        <td><code>async_update_action</code></td><td>YES</td>
        <td>
            Update an ation's progress, wake up all monitoring client against this action.<br /><br />
            Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The action has been updated, all monitoring client against this action has been woken up</td>
</tr>
<tr>
<td>NOT_FOUND</td>
<td>The action is not found based on the action ID caller provided.</td>
</tr>
<tr>
<td>ACTION_COMPLETED</td>
<td>The action has already been completed</td>
</tr>
</tr>
<tr>
<td>DB_FAILED</td>
<td>Cannot save the progress for the action to database, probably check your DB configuration and connectivity</td>
</tr>
<br/>
</table>
        </td>
    </tr>
    <tr>
        <td><code>async_complete_action</code></td>
        <td>YES</td>
        <td>
            Complete an ation and set it's result, wake up all monitoring client against this action.<br /><br />
            Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The action has been completed, all monitoring client against this action has been woken up</td>
</tr>
<tr>
<td>NOT_FOUND</td>
<td>The action is not found based on the action ID caller provided.</td>
</tr>
<tr>
<td>ACTION_COMPLETED</td>
<td>The action has already been completed</td>
</tr>
</tr>
<tr>
<td>DB_FAILED</td>
<td>Cannot save the progress for the action to database, probably check your DB configuration and connectivity</td>
</tr>
<br/>
</table>
        </td>
    </tr>
<tr>
    <td><code>async_wait_for_action_update</code></td><td>YES</td>
    <td>wait for an action to be updated or completed<br/><br/>
    Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The action has been updated or completed</td>
</tr>
<tr>
<td>NOT_FOUND</td>
<td>The action is not found based on the action ID caller provided.</td>
</tr>
<tr>
<td>ACTION_COMPLETED</td>
<td>The action has already been completed</td>
</tr>
</tr>
<tr>
<td>TIMEDOUT</td>
<td>The action has not been updated or completed within the timeout caller specified</td>
</tr>
<br/>
</table>
    </td>
</tr>
<tr>
    <td><code>start_action</code></td><td>No</td><td>non-async version of <code>async_start_action</code></td>
</tr>
<tr>
    <td><code>update_action</code></td><td>No</td><td>non-async version of <code>async_update_action</code></td>
</tr>
<tr>
    <td><code>complete_action</code></td><td>No</td><td>non-async version of <code>async_complete_action</code></td>
</tr>
</table>

# Action Handlers
## CLIActionHandler
* [Details](src/webcli2/action_handlers/spark/README.md)
## MermaidHandler
* [Details](src/webcli2/action_handlers/mermaid/README.md)