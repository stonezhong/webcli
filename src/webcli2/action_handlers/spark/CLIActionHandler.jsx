import React from 'react';
import BaseActionHandler from './BaseActionHandler';

export default class CLIActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "spark";
    }

    getRequestFromCommandText(commandText) {
        const lines = commandText.trim().split("\n")
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
                command_text: commandText
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
