import React from 'react';
import BaseActionHandler from './BaseActionHandler';
import Alert from 'react-bootstrap/Alert';

class ConfigRequest {
    constructor({actionHandlerName, mode, clientId, newConfig={}}) {
        this.mode = mode; // either "get" or "set"
        this.actionHandlerName = actionHandlerName;
        this.clientId = clientId;
        this.newConfig = newConfig; // JSON sring
    }
}

class ConfigResponse {
    constructor({error="", config={}}) {
        this.error = error;
        this.config = config; // JSON object
    }
}

/********************************************************************************
 * This action handler allows you to display or update other action handler's 
 * configuration
 * 
 * syntax to display config:
 * %config% get ${action_handler_name}
 * 
 * syntax to update config
 * %config% set ${action_handler_name}
 * configuration in JSON format
 * 
 */
export default class ConfigActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "config";
    }

    // perform the action and return ConfigResponse, request is a ConfigRequest
    async doAction(request) {
        console.log("ConfigActionHandler.doAction: enter, request=", request);

        if (request.mode === "get") {
            console.log("ConfigActionHandler.doAction: mode = get");
            const [error, config] = this.manager.getConfig(request.actionHandlerName);
            const response = new ConfigResponse({error:error, config:config});
            console.log("ConfigActionHandler.doAction: exit, response=", response);
            return response;
        }

        if (request.mode === "set") {
            console.log("ConfigActionHandler.doAction: mode = set");
            const httpResponse = await fetch(`/configurations/${request.actionHandlerName}/${this.clientId}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: request.newConfig,
            });

            if (!httpResponse.ok) {
                // we are not able to set config
                console.log("ConfigActionHandler.doAction: error, ", httpResponse);
                const response = new ConfigResponse({
                    error:`Unable to set config for ${request.actionHandlerName}`
                });

                console.log("ConfigActionHandler.doAction: exit, response=", response);
                return response;
            }

            const newConfigModel = await httpResponse.json();
            const response = new ConfigResponse({
                config: newConfigModel.configuration
            });
            this.manager.setConfig(request.actionHandlerName, newConfigModel.configuration);
            console.log("ConfigActionHandler.doAction: exit, response=", response);
            return response;
        }

        throw new Error("bad mode");
    }

    // return ConfigRequest if the command is recognized, or null
    getRequestFromCommandText(commandText) {
        const lines = commandText.split("\n")
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
                mode: "get",
                clientId: this.clientId,
                actionHandlerName: args[2]
            });
        }

        if (args[1] == "set") {
            return new ConfigRequest({
                mode: "set",
                clientId: this.clientId,
                actionHandlerName: args[2],
                newConfig: lines.slice(1).join("\n")
            });
        }

        return null;
    }

    renderAction(action) {
        if (action.response.error) {
            return <Alert variant="warning">
                {action.response.error}
            </Alert>
        }

        return <pre>
            {JSON.stringify(action.response.config, null, 2)}
        </pre>;
    }
}
