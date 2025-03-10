function get_patch_value(value) {
    if (typeof value === "undefined") {
        return null;
    }
    return {value:value};
}

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
        body: JSON.stringify({title: get_patch_value(title)}),
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
        body: JSON.stringify({description: get_patch_value(description)}),
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
        body: JSON.stringify({title:get_patch_value(title)}),
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
        body: JSON.stringify({show_question:get_patch_value(show_question)}),
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
        body: JSON.stringify({show_answer:get_patch_value(show_answer)}),
    });
    if (!response.ok) {
        throw new Error(`Failed to update action title: ${response.status}`);
    }
    await response.json();
}

export async function move_thread_action_up({thread_action_id}) {
    const response = await fetch(`/apis/thread_actions/move/${thread_action_id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({direction: "up"}),
    });
    if (!response.ok) {
        throw new Error(`Failed to move thread_action up: ${response.status}`);
    }
    await response.json();
}

export async function move_thread_action_down({thread_action_id}) {
    const response = await fetch(`/apis/thread_actions/move/${thread_action_id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({direction: "down"}),
    });
    if (!response.ok) {
        throw new Error(`Failed to move thread_action down: ${response.status}`);
    }
    await response.json();
}
