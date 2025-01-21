import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

import {WebCLIClient} from './tools/webcli_client';
import ConfigActionHandler from "./tools/ConfigActionHandler";
import MermaidActionHandler from "./tools/MermaidActionHandler";

const client_id = document.querySelector('meta[name="client-id"]').content;
const websocket_uri = document.querySelector('meta[name="websocket-uri"]').content;
const configMap = JSON.parse(document.querySelector('meta[name="config-map"]').content);

function setActionHandlerConfig(actionHandler) {
    const actionHandlerName = actionHandler.getName();
    const config = (actionHandlerName in configMap)?configMap[actionHandlerName].configuration:{};
    actionHandler.setConfig(config);
}

const webCLIClient = new WebCLIClient({
    "url": websocket_uri,
    "client_id": client_id,
});


// register mermaid action handler
var actionHandler;

actionHandler = new ConfigActionHandler(client_id);
setActionHandlerConfig(actionHandler);
webCLIClient.registerActionHandler(actionHandler);

actionHandler = new MermaidActionHandler(client_id);
setActionHandlerConfig(actionHandler);
webCLIClient.registerActionHandler(actionHandler);

const domNode = document.getElementById('root');
const root = createRoot(domNode);
root.render(<App 
    webCLIClient={webCLIClient} 
/>);
