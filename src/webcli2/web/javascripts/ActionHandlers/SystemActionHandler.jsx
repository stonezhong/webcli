import React from 'react';
import {BaseActionHandler} from './webcli_client';
import ReactMarkdown from "react-markdown";


/********************************************************************************
 * The System Action Handler client
 * 
 */
export default class SystemActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "system";
    }

    getActionRequestFromText(text) {
        const lines = text.split("\n")
        if (lines.length == 0) {
            return null;
        }

        const title = lines[0].trim();
        const verb = title.split(" ")[0];
        const args = title.slice(verb.length).trim();
        if (!["%markdown%", "%html%", "%mermaid%", "%config%", "%python%"].includes(verb)) {
            return null;
        }

        const request = {
            type: verb.slice(1, -1),
            client_id: this.clientId,
            command_text: lines.slice(1).join("\n"),
            args: args
        }
        return request;
    }
}
