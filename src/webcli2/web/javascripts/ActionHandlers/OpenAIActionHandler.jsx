import React from 'react';
import {BaseActionHandler} from './webcli_client';
import ReactMarkdown from "react-markdown";


/********************************************************************************
 * This action handler allows you to send question to OpenAI
 * 
 * syntax
 * %openai%
 * question
 * 
 */
export default class MermaidActionHandler extends BaseActionHandler {
    constructor(clientId) {
        super(clientId);
    }

    getName() {
        return "openai";
    }

    getActionRequestFromText(text) {
        const lines = text.split("\n")
        if (lines.length == 0) {
            return null;
        }

        const title = lines[0].trim()
        if (!["%openai%"].includes(title)) {
            return null;
        }

        const request = {
            type: title.slice(1, -1),
            client_id: this.clientId,
            command_text: lines.slice(1).join("\n")
        }
        return request;
    }

    renderAction(action) {
        return <ReactMarkdown>{action.response.message}</ReactMarkdown>;
    }
}


