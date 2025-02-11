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
        if (!["%openai%", "%python%"].includes(title)) {
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
        return <div>
            {action.response.chunks.map(chunk => {
                if ((chunk.mime === "text/html")||(chunk.mime === "image/png")) {
                    return <div dangerouslySetInnerHTML={{ __html: chunk.content }} />;
                } else if (chunk.mime === "text/json") {
                    try {
                        const json_content = JSON.parse(chunk.content);
                        return <pre>{JSON.stringify(json_content, null, 4)}</pre>
                    }
                    catch (err) {
                        return <pre>{err.message}</pre>
                    }
                } else if (chunk.mime === "text/markdown") {
                    return <ReactMarkdown>{chunk.content}</ReactMarkdown>;
                } else if (chunk.mime === "text/plain") {
                    return <pre>{chunk.content}</pre>
                } else {
                    throw new Error(`Unrecognized chunk: ${chunk.mime}`);
                }       
            })}
        </div>;
    }
}
