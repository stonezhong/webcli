import React from 'react';
import { createRoot } from 'react-dom/client';
import { HomePage } from './Pages/HomePage';
import { StrictMode } from 'react';
import MermaidActionHandler from "./ActionHandlers/MermaidActionHandler";
import PySparkActionHandler from "./ActionHandlers/PySparkActionHandler";
import ConfigActionHandler from './ActionHandlers/ConfigActionHandler';

const thread_id = parseInt(document.querySelector('meta[name="thread-id"]').content);
const client_id = document.querySelector('meta[name="client-id"]').content;
const websocket_uri = document.querySelector('meta[name="websocket-uri"]').content;
const configMap = JSON.parse(document.querySelector('meta[name="config-map"]').content);

function setActionHandlerConfig(actionHandler) {
    const actionHandlerName = actionHandler.getName();
    const config = (actionHandlerName in configMap)?configMap[actionHandlerName].configuration:{};
    actionHandler.setConfig(config);
}


// register action handlers

const actionHandlerMap = new Map();
var actionHandler = null;

// initialize all action handlers
actionHandler = new ConfigActionHandler(client_id);
setActionHandlerConfig(actionHandler);
actionHandlerMap.set(actionHandler.getName(), actionHandler);
actionHandler.actionHandlerMap = actionHandlerMap;

actionHandler = new MermaidActionHandler(client_id);
setActionHandlerConfig(actionHandler);
actionHandlerMap.set(actionHandler.getName(), actionHandler);

actionHandler = new PySparkActionHandler(client_id);
setActionHandlerConfig(actionHandler);
actionHandlerMap.set(actionHandler.getName(), actionHandler);

const domNode = document.getElementById('webcli');
const root = createRoot(domNode);
root.render(
    <HomePage
        wsUrl={websocket_uri}
        clientId={client_id}
        actionHandlerMap={actionHandlerMap}
        threadId={thread_id}
    />
);

// root.render(
//     <StrictMode>
//         <App 
//             webCLIClient={webCLIClient} 
//         />
//     </StrictMode>    
// );
