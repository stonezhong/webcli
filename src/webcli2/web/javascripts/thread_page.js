import React from 'react';
import { createRoot } from 'react-dom/client';
import { ThreadPage } from './Pages/ThreadPage';
import SystemActionHandler from "./ActionHandlers/SystemActionHandler";
import PySparkActionHandler from "./ActionHandlers/PySparkActionHandler";
import OpenAIActionHandler from './ActionHandlers/OpenAIActionHandler';


const thread_id = parseInt(document.querySelector('meta[name="thread-id"]').content);
const client_id = document.querySelector('meta[name="client-id"]').content;
const websocket_uri = document.querySelector('meta[name="websocket-uri"]').content;

// register action handlers

const actionHandlerMap = new Map();
var actionHandler = null;

// initialize all action handlers
actionHandler = new SystemActionHandler(client_id);
actionHandlerMap.set(actionHandler.getName(), actionHandler);

actionHandler = new PySparkActionHandler(client_id);
actionHandlerMap.set(actionHandler.getName(), actionHandler);

actionHandler = new OpenAIActionHandler(client_id);
actionHandlerMap.set(actionHandler.getName(), actionHandler);

const domNode = document.getElementById('webcli');
const root = createRoot(domNode);
root.render(
    <ThreadPage
        wsUrl={websocket_uri}
        clientId={client_id}
        actionHandlerMap={actionHandlerMap}
        threadId={thread_id}
    />
);
