import React from 'react';
import {BaseActionHandler} from './webcli_client';

export default class PySparkActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "pyspark";
    }

    getActionRequestFromText(text) {
        const lines = text.trim().split("\n")
        if (lines.length == 0) {
            return null;
        }

        const title = lines[0].trim()
        if ((title === "%pyspark%") || (title === "%bash%") || (title === "%system%")) {
            // we are talking to spark server
            return {
                type: "spark-cli",
                client_id: this.clientId,
                command_text: text
            };
        }

        return null;
    }
}
