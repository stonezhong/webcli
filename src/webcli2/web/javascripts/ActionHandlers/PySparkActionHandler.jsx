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

        const title = lines[0]
        if ((title.trim() === "%pyspark%") || (title.trim() === "%bash%") || (title.trim() === "%system%")) {
            // we are talking to spark server
            return {
                type: "spark-cli",
                client_id: this.clientId,
                server_id: this.config.server_id,
                command_text: text
            };
        }

        return null;
    }

    renderAction(action) {
        return <pre>
            {action.response.cli_package.reply_message}
        </pre>;
    }
}
