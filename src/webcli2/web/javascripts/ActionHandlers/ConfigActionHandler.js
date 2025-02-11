import React from 'react';
import {BaseActionHandler} from './webcli_client';

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
            return {
                type: "config",
                client_id: this.clientId,
                action: "get",
                action_handler_name: args[2],
                content: null
            };
        }

        if (args[1] == "set") {
            return {
                type: "config",
                client_id: this.clientId,
                action: "set",
                action_handler_name: args[2],
                content: lines.slice(1).join("\n")
            };
        }

        return null;
    }

    renderAction(action) {
        if (action.response.succeeded) {
            return <pre>{action.response.content}</pre>;
        }

        return <pre>{`Error: ${action.response.error_message}`}</pre>;
    }
}
