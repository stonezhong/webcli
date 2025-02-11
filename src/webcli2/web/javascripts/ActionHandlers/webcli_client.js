import pino from 'pino';

const logger = pino({
    level: 'debug',
    transport: {
        target: 'pino-pretty',
        options: { colorize: true },
    },
});

export class BaseActionHandler {
    constructor(clientId) {
        this.clientId = clientId;
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
     * Called when an action is completed
     * action:   The action object. An Action instance, but response is null
     * response: The response from server
     */
    async onActionCompleted(action, response) {
        // derived class can override this behavior if needed
        action.response = response;
    }
}
