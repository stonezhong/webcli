import React from 'react';
import {BaseActionHandler} from './webcli_client';

class ConfigRequest {
    constructor({client_id, action, action_handler_name, content=null}) {
        this.type = "config";
        this.client_id = client_id;
        this.action = action;
        this.action_handler_name = action_handler_name;
        this.content = content;
    }
}

/********************************************************************************
 * This action handler allows you to get and set configs
 * 
 * syntax
 * %config% set <action handler name>
 * content
 * 
 * or
 * 
 * %config% get <action handler name>
 */
export default class ConfigActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "config";
    }

    getActionRequestFromText(text) {
        const lines = text.split("\n")
        if (lines.length == 0) {
            return null;
        }

        const args = lines[0].split(" ");
        if (args[0] !== '%config%') {
            return null;
        }

        if (args.length != 3) {
            return null;
        }

        if ((args[1] != "get") && (args[1] != "set")) {
            return null;
        }

        if (args[1] == "get") {
            return new ConfigRequest({
                client_id: this.clientId,
                action: "get",
                action_handler_name: args[2],
                content: null
            });
        }

        if (args[1] == "set") {
            return new ConfigRequest({
                client_id: this.clientId,
                action: "set",
                action_handler_name: args[2],
                content: lines.slice(1).join("\n")
            });
        }

        return null;
    }

    renderAction(action) {
        if (action.response.succeeded) {
            return <pre>{action.response.content}</pre>;
        }

        return <pre>{`Error: ${action.response.error_message}`}</pre>;
    }

    /*******************
     * Get action handler's config, if found, return a JSON for the config
     * otherwise, return null.
     */
    getActionHandlerConfig(actionHandlerName) {
        if (!this.actionHandlerMap.has(actionHandlerName)) {
            return null;
        }
        return this.actionHandlerMap.get(actionHandlerName).getConfig();
    }

    /*******************
     * Set action handler config
     */
    setActionHandlerConfig(actionHandlerName, config) {
        if (!this.actionHandlerMap.has(actionHandlerName)) {
            return;
        }
        this.actionHandlerMap.get(actionHandlerName).setConfig(config);
    }

    /*********************************************
     * Called when an action is completed
     * action:   The action object. An Action instance, but response is null
     * response: The response from server
     */
    async onActionCompleted(action, response) {
        const actionHandlerName = action.handler_name;
        if (action.request.action === "get") {
            const config = this.getActionHandlerConfig(actionHandlerName);
            if (config === null) {
                action.response = {
                    succeeded: false,
                    error_message: `action handler ${actionHandlerName} does not exist!`
                }
                return;
            }
            action.response = {
                succeeded: true,
                content: JSON.stringify(config, null, 4)
            }
            return;
        }

        action.response = response;
        if (response.succeeded) {
            const config = JSON.parse(response.content);
            this.setActionHandlerConfig(actionHandlerName, config);
        }
        return;
    }
}
