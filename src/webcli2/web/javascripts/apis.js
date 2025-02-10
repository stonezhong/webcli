export async function list_threads() {
    /***************
     * Return:
     * List of Thread
     */
    const response = await fetch("/apis/threads", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        }
    });

    const ret = await response.json();
    return ret;
}

export async function get_thread(id) {
    /***************
     * Return:
     * Thread or null
     */
    const response = await fetch(`/apis/threads/${id}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        }
    });

    if (response.status === 404) {
        return null;
    }

    const ret = await response.json();
    return ret;
}

export async function create_thread({title, description}) {
    /***************
     * Return:
     * Thread
     */
    const response = await fetch(`/apis/threads`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({title, description}),
    });
    if (!response.ok) {
        throw new Error(`create_thread: Failed to send action to server, status: ${response.status}`);
    }
    const thread = await response.json();
    return thread;

}

export async function update_thread_title({thread_id, title}) {
    const response = await fetch(`/apis/threads/${thread_id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({title}),
    });
    if (!response.ok) {
        throw new Error(`update_thread_title: Failed to update thread title: ${response.status}`);
    }
    await response.json();
}

export async function update_thread_description({thread_id, description}) {
    const response = await fetch(`/apis/threads/${thread_id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({description}),
    });
    if (!response.ok) {
        throw new Error(`update_thread_description: Failed to update thread description: ${response.status}`);
    }
    await response.json();
}


export async function delete_thread({id}) {
    /***************
     * Return:
     * None
     */
    const response = await fetch(`/apis/threads/${id}`, {
        method: "DELETE",
        headers: {
            "Content-Type": "application/json",
        },
    });
    if (!response.ok) {
        throw new Error(`delete_thread: Failed to send action to server, status: ${response.status}`);
    }
    const r = await response.json();
    return null;

}

export async function create_action({thread_id, request, title, raw_text}) {
    const response = await fetch(`/apis/threads/${thread_id}/actions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({request, title, raw_text}),
    });
    if (!response.ok) {
        throw new Error(`Failed to send action to server, status: ${response.status}`);
    }
    const threadAction = await response.json();
    return threadAction;
}

export async function remove_action_from_thread({thread_id, action_id}) {
    /**
     * It does not delete the action, just detach the action from thread
     */
    const response = await fetch(`/apis/threads/${thread_id}/actions/${action_id}`, {
        method: "DELETE",
        headers: {
            "Content-Type": "application/json",
        },
    });
    if (!response.ok) {
        throw new Error(`Failed to remove action from thread: ${response.status}`);
    }
    await response.json();
}

export async function update_action_title({action_id, title}) {
    const response = await fetch(`/apis/actions/${action_id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({title:title}),
    });
    if (!response.ok) {
        throw new Error(`Failed to update action title: ${response.status}`);
    }
    await response.json();
}

export async function update_thread_action_show_question({thread_id, action_id, show_question}) {
    const response = await fetch(`/apis/threads/${thread_id}/actions/${action_id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({show_question}),
    });
    if (!response.ok) {
        throw new Error(`Failed to update action title: ${response.status}`);
    }
    await response.json();
}

export async function update_thread_action_show_answer({thread_id, action_id, show_answer}) {
    const response = await fetch(`/apis/threads/${thread_id}/actions/${action_id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({show_answer}),
    });
    if (!response.ok) {
        throw new Error(`Failed to update action title: ${response.status}`);
    }
    await response.json();
}
