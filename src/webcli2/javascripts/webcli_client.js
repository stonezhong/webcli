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
     * client_id        : str, a unique ID represent a client
     * url              : web socket URL, e.g. ws://localhost:8000/ws
     * onActionCompleted: an async function, called when we receive a signal that an action is completed
     *                   from web socket
     */
    constructor({url, client_id}) {
        this.url = url;
        this.client_id = client_id;
        this.socket = null;
        this.onActionCompleted = null;
        this.actionHandlerMap = new Map();
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
            return <div key={action.id}>
                <pre>{action.text}</pre>
                <hr />
            </div>;
        }
        const actionHandler = this.actionHandlerMap.get(action.handlerName);
        return <div key={action.id}>
            <pre>{action.text}</pre>
            {actionHandler.renderAction(action)}
            <hr />
        </div>;
    }
    
    /*******************
     * Connecto to web socket
     * onActionCompleted: called upon success
     * 
     */
    connect(onActionCompleted) {
        logger.info("WebCLIClient.connect: enter");
        if (this.socket !== null) {
            throw new Error("WebSocket is already connected!");
        }

        this.socket = new WebSocket(this.url);
        this.onActionCompleted = onActionCompleted;

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
    }

    setConfig(config) {
        this.config = structuredClone(config);
    }

    getConfig() {
        return structuredClone(this.config);
    }

    getName() {
        throw new Exception("derived class to implement");
    }

    getActionRequestFromText(text) {
        throw new Exception("derived class to implement");
    }

    renderAction(action) {
        throw new Exception("derived class to implement");
    }
}
