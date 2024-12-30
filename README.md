# Index
* [Concepts](#concepts)
    * [Async Action](#async-action)

# Concepts
## Async Action

An async action, like the name implies, prepresent an async action.
* When an async action is created, request field stores the context on what is action is about. It is a JSON object.
* When an async action is completed -- either successfully or failed, the response field store the action result. It is a JSON object
* Once an async action is created, before it is completed, you can update the progress information, it is stored in progress field. It is a JSON field.

# APIs
## CLIHandler
<table>
    <tr><th>Name</th><th>Async</th><th>Description</th></tr>
    <tr>
        <td>
            <code>async_start_async_action</code>
        </td>
        <td>
        YES
        </td>
        <td>
            Create an async action. It returns a tuple of status and async action being created. status type is AsyncActionOpStatus.
            If async action is created successfully, status will be <code>AsyncActionOpStatus.OK</code>, and an async action will be returned, the returned async action has already been saved to database.<br /><br />
            CLIHandler rely on a list of customer defined handlers to handle the request. handler's <code>can_handle</code> method looks at the action's request and judge if it can handle it or not.<br /><br />
            Once an async action is created, the handler's <code>handle</code> method has been scheduled in a threadpool. The handler's <code>handle</code> method is suppose to take care of the execution of the async action<br/><br/>
            Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The async action has been created, the AsyncAction object is returned. The customer action handler's <code>handle</code> method has been scheduled in a thread pool</td>
</tr>
<tr>
<td>SHUTDOWN_IN_PROGRESS</td>
<td>This means the CLIHandler is in the progress of shutdown and does not serve creating new async actions.</td>
</tr>
<tr>
<td>NO_HANDLER</td>
<td>Cannot find a handler that can handle this async action. You need to make sure when you create CLIHandler, <code>action_handlers</code> is set properly</td>
</tr>
</tr>
<tr>
<td>DB_FAILED</td>
<td>Cannot save the async action to database, probably check your DB configuration and connectivity</td>
</tr>
<br/>
</table>
        </td>
    </tr>
    <tr>
        <td>
            <code>async_update_progress_async_action</code>
        </td>
        <td>
        YES
        </td>
        <td>
            Update an async ation's progress, wake up all monitoring client against this async action.<br /><br />
            Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The async action has been updated, all monitoring client against this async action has been woken up</td>
</tr>
<tr>
<td>NOT_FOUND</td>
<td>The async action is not found based on the action ID caller provided.</td>
</tr>
<tr>
<td>ACTION_COMPLETED</td>
<td>The async action has already been completed</td>
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
        <td>
            <code>async_complete_async_action</code>
        </td>
        <td>
        YES
        </td>
        <td>
            Complete an async ation and set it's result, wake up all monitoring client against this async action.<br /><br />
            Here is a list of possible status based on status
<table>
<tr>
<th>Status</th>
<th>Reason</th>
</tr>
<tr>
<td>OK</td>
<td>The async action has been completed, all monitoring client against this async action has been woken up</td>
</tr>
<tr>
<td>NOT_FOUND</td>
<td>The async action is not found based on the action ID caller provided.</td>
</tr>
<tr>
<td>ACTION_COMPLETED</td>
<td>The async action has already been completed</td>
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
</table>