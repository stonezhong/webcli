import React from 'react';
import {BaseActionHandler} from './webcli_client';

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

    getActionRequestFromText(text) {
        const lines = text.split("\n")
        if (lines.length == 0) {
            return null;
        }

        const title = lines[0]
        if (title.trim() == "%mermaid%") {
            // we are trying to show a diagram
            // this MUST match MermaidRequest class in python
            const request = {
                type: "mermaid",
                client_id: this.clientId,
                command_text: text                
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


