import React from 'react';
import pino from 'pino';

const logger = pino({
    level: 'debug',
    transport: {
        target: 'pino-pretty',
        options: { colorize: true },
    },
});


export class Action {
    /*******************
     * Every action has a unique ID
     * text, a string, the original text human input for the action
     * request is a JSON, capture the request for the action
     * response is a JSON, capture the response for the action. If an action is pending, the response is null
     * handlerName: the name of the action handler.
    */
    constructor({id, text, request, handlerName}) {
        this.id = id;
        this.text = text
        this.request = request;
        this.handlerName = handlerName;
        this.response = null;
    }
}


export class WebCLIClient {
    /*******************
     * client_id       : str, a unique ID represent a client
     * url             : web socket URL, e.g. ws://localhost:8000/ws
     * onActionsUpdated: an async function, to notify UI component it need to re-render
     * actions         : tracks all actions
     * renderPendingAction: a method provided by caller, when an action is pending answer, this show s a loading icon
     */
    constructor({url, client_id}) {
        this.url = url;
        this.client_id = client_id;
        this.socket = null;
        this.onActionsUpdated = null;
        this.actionHandlerMap = new Map();
        this.actions = [];
        this.renderPendingAction = (action) => <div>Loading result ...</div>;
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

    async addAction(action) {
        this.actions.push(action);
        await this.onActionsUpdated();
    }

    /*******************
     * Register an action handler. Every action handler MUST have a unique name.
     */
    registerActionHandler(actionHandler) {
        const name = actionHandler.getName();
        if (this.actionHandlerMap.has(name)) {
            throw new Error(`action handler ${name} is already registered`);
        }

        this.actionHandlerMap.set(name, actionHandler);
        actionHandler.onRegister(this);
    }

    /******************************************************************************
     * Given a piece of text, try to find if an action handler can recognize it
     ******************************************************************************/
    getActionRequestFromText(text) {
        for (const actionHandler of this.actionHandlerMap.values()) {
            const request = actionHandler.getActionRequestFromText(text);
            if (request !== null) {
                return [actionHandler, request];
            }
        }
        return [null, null];
    }

    /**********************************************************************************
     * Render an action
     * action: Action
     * We let the action to render the request and response
     */
    renderAction(action) {
        if (action.response === null) {
            return <div>
                <pre>{action.text}</pre>
                {this.renderPendingAction(action)}
            </div>;
        }
        const actionHandler = this.actionHandlerMap.get(action.handlerName);
        return <div>
            <pre>{action.text}</pre>
            {actionHandler.renderAction(action)}
        </div>;
    }


    /*******************
     * name: The name of the action handler
     * action: the action
     * 
     */
    async onActionCompleted(actionId, response) {
        logger.info("WebCLIClient.onActionCompleted: enter");

        // in javascript, array.map does not support async function
        const newActions = [];
        for (const action of this.actions) {
            if (action.id !== actionId) {
                newActions.push(action);
                continue;
            }

            const newAction = new Action({
                id: action.id,
                text: action.text,
                request: action.request,
                handlerName: action.handlerName
            });
            const actionHandler = this.actionHandlerMap.get(action.handlerName);
            await actionHandler.onActionCompleted(newAction, response);
            newActions.push(newAction);
        }
        this.actions = newActions;

        await this.onActionsUpdated();

        logger.info("WebCLIClient.onActionCompleted: exit");
    }
    
    /*******************
     * Connecto to web socket
     * onActionCompleted: called upon success
     * 
     */
    connect(onActionsUpdated, renderPendingAction) {
        logger.info("WebCLIClient.connect: enter");
        if (this.socket !== null) {
            throw new Error("WebSocket is already connected!");
        }

        this.socket = new WebSocket(this.url);
        this.onActionsUpdated = onActionsUpdated;
        this.renderPendingAction = renderPendingAction;

        // Event: Connection opened
        this.socket.addEventListener("open", () => {
            logger.info("websocket.open: enter");
            this.socket.send(JSON.stringify({ client_id: this.client_id }));
            logger.info("websocket.open: exit");
        });

        // Event: Connection closed
        this.socket.addEventListener("close", (event) => {
            logger.info("websocket.close: enter");
            logger.info(`websocket.close: connection closed (Code: ${event.code}, Reason: ${event.reason})`);
            logger.info("websocket.close: exit");           
        });

        // Event: Error
        this.socket.addEventListener("error", (error) => {
            logger.info("websocket.error: enter");
            logger.info("websocket.error: ", error);
            logger.info("websocket.error: enter");
        });

        // Event: Message received
        this.socket.addEventListener("message", async (event) => {
            logger.info("websocket.message: enter");
            logger.info("websocket.message: received ", event.data);
            try {
                if (event.data == "ping") {
                    logger.info("websocket.message: ping from server, ignore");
                    logger.info("websocket.message: exit");
                    return;
                }
                const parsedData = JSON.parse(event.data);
                logger.info("websocket.message: parsed ", parsedData);
                await this.onActionCompleted(parsedData.action_id, parsedData.response);
            } catch (error) {
                error("websocket.message: parse JSON error ", error);
            }
            logger.info("websocket.message: exit");
        });
        logger.info("WebCLIClient.connect: exit");
    }

}

export class BaseActionHandler {
    constructor(clientId) {
        this.clientId = clientId;
        this.config = {};
        this.webcliClient = null;
    }

    /*********************************************
     * Update the config of an action handler
     */
    setConfig(config) {
        this.config = structuredClone(config);
    }

    /*********************************************
     * Return the config of an action handler, the config is a JSON object
     */
    getConfig() {
        return structuredClone(this.config);
    }

    /*********************************************
     * Return the name of an action handler
     */
    getName() {
        throw new Exception("derived class to implement");
    }

    /*********************************************
     * As an action hanlder, you need to tell if you can recognize the 
     * text and extract an Action object from it
     */
    getActionRequestFromText(text) {
        throw new Exception("derived class to implement");
    }

    /*********************************************
     * Render an action
     */
    renderAction(action) {
        throw new Exception("derived class to implement");
    }

    /*********************************************
     * Called when an action is registered via registerActionHandler
     */
    onRegister(webCliClient) {
        this.webcliClient = webCliClient;
    }

    /*********************************************
     * Called when an action is completed
     * action:   The action object. An Action instance, but response is null
     * response: The response from server
     */
    async onActionCompleted(action, response) {
        // derived class can override this behavior if needed
        action.response = response;
    }
}
