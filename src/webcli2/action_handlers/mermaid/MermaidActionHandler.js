import React from 'react';
import BaseActionHandler from './BaseActionHandler';

/********************************************************************************
 * This action handler allows you to display mermaid graph
 * 
 * syntax
 * %mermaid%
 * mermaid contents
 * 
 */
export default class MermaidActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "mermaid";
    }

    getRequestFromCommandText(commandText) {
        const lines = commandText.split("\n")
        if (lines.length == 0) {
            return null;
        }

        const title = lines[0]
        if (title.trim() == "%mermaid%") {
            // we are trying to show a diagram
            const request = {
                type: "mermaid",
                client_id: this.clientId,
                command_text: commandText                
            }
            return request;
        }

        return null;
    }

    renderAction(action) {
        const htmlContent = action.response.svg;
        return <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
    }
}
