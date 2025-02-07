import React, { useEffect, useRef } from 'react';
import {BaseActionHandler} from './webcli_client';
import ReactMarkdown from "react-markdown";
import mermaid from 'mermaid';

const MermaidDiagram = ({ chart }) => {
    const ref = useRef(null);

    useEffect(() => {
        mermaid.initialize({ startOnLoad: true });
        mermaid.run();
    }, [chart]);

    return <div className="mermaid" ref={ref}>{chart}</div>;
};

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

        const title = lines[0].trim()
        if (!["%html%", "%mermaid%", "%markdown%"].includes(title)) {
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
        if (action.response.type === "html") {
            return <div dangerouslySetInnerHTML={{ __html: action.response.content }} />;
        }
        if (action.response.type === "markdown") {
            return <ReactMarkdown>{action.response.content}</ReactMarkdown>;
        }
        if (action.response.type === "mermaid") {
            return <MermaidDiagram chart={action.response.content} />;
        }
        return null;
    }
}


