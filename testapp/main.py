#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

import os
import json
import uuid
from contextlib import asynccontextmanager

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from webcli2 import WebCLIEngine, WebSocketConnectionManager, WebCLIEngineStatus
from webcli2.action_handlers.mermaid import MermaidHandler
from webcli2.action_handlers.config import ConfigHandler
from webcli2.db_models import create_all_tables

WEB_SOCKET_URI = "ws://localhost:8000/ws"

##########################################################
# create a WebCLIEngine, config action handlers if needed
##########################################################
engine = create_engine(f"sqlite:///{os.path.join(BASE_DIR, "test.db")}")
create_all_tables(engine)

webcli_engine = WebCLIEngine(
    db_engine = engine,
    wsc_manager=WebSocketConnectionManager(),
    action_handlers=[
        ConfigHandler(),
        MermaidHandler()
    ]
)


##########################################################
# Create a FastAPI application
# make sure we startup and shutdown webcli engine
# when FastAPI app starts and shutdown
##########################################################
@asynccontextmanager
async def lifespan(app: FastAPI):
    webcli_engine.startup()
    yield
    webcli_engine.shutdown()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dist", StaticFiles(directory="dist"), name="dist")
templates = Jinja2Templates(directory="dist/templates")


##########################################################
# Endpoint for client to create actions
##########################################################
@app.post("/actions")
async def handle_action(request: dict):
    logger.debug(f"handle_action: enter")
    status, aciton = await webcli_engine.async_start_action(request)
    logger.debug(f"handle_action: exit")
    if status == WebCLIEngineStatus.OK:
        return {
            "id": aciton.id
        }
    if status == WebCLIEngineStatus.NO_HANDLER:
        raise HTTPException(status_code=400, detail="No handler is registered for the action you requested")

    raise HTTPException(status_code=500, detail=f"Internal server error, status = {status}")

##########################################################
# Endpoint for websocket
##########################################################
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await webcli_engine.wsc_manager.websocket_endpoint(websocket)

##########################################################
# Endpoint for homepage
##########################################################
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    # generate client ID
    client_id = request.cookies.get("client-id")
    set_client_id = False
    if client_id is None:
        client_id = str(uuid.uuid4())
        set_client_id = True

    # send action handler configuration to client
    ahcs = await webcli_engine.get_action_handler_configurations(client_id)
    config_map = {
        ahc.action_handler_name: ahc.model_dump(mode='json') for ahc in ahcs
    }

    response = templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Home Page",
            "websocket_uri": WEB_SOCKET_URI,
            "client_id": client_id,
            "config_map": json.dumps(config_map)
        }
    )
    if set_client_id:
        response.set_cookie(
            key="client-id",
            value=client_id,
            max_age=86400*365*10,   # cookie lasts 10 year
            path="/",               # optional: root path
            secure=False,           # optional: send only over HTTPS if True
            httponly=False,         # optional: not accessible via client-side JS
            samesite="strict",      # optional: 'strict' | 'lax' | 'none'
        )
 
    return response
