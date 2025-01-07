import React from 'react';

export default class BaseActionHandler {
    constructor(clientId) {
        this.clientId = clientId;
        this.config = {};
        this.manager = null;
    }

    setConfig(config) {
        this.config = structuredClone(config);
    }

    getConfig() {
        return structuredClone(this.config);
    }

    onRegister(manager) {
        this.manager = manager;
    }

    getName() {
        throw new Exception("derived class to implement");
    }

    getRequestFromCommandText(commandText) {
        throw new Exception("derived class to implement");
    }

    renderAction(action) {
        throw new Exception("derived class to implement");
    }
}
