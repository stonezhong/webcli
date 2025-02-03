#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

import os
import importlib
import asyncio
import uuid
import json

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from contextlib import asynccontextmanager

from webcli2 import WebCLIEngine, WebCLIEngineStatus, WebSocketConnectionManager
from webcli2.action_handlers.config import ConfigHandler
from webcli2.db_models import create_all_tables
from fastapi import WebSocket

from webcli2.config import load_config

##########################################################
# WEB_DIR is the directory of web insode webcli2 package
##########################################################
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

config = load_config()

##########################################################
# Loading all action handlers
# We will install ConfigHandler anyway
##########################################################
action_handlers = [ConfigHandler()]
for action_handler_name, action_handler_info in config.core.action_handlers.items():
    logger.info(f"Loading action handler: name={action_handler_name}, module={action_handler_info.module_name}, class={action_handler_info.class_name}")
    module = importlib.import_module(action_handler_info.module_name)
    klass = getattr(module, action_handler_info.class_name)
    action_handler = klass(**action_handler_info.config)
    action_handlers.append(action_handler)

##########################################################
# create a WebCLIEngine
##########################################################
engine = create_engine(config.core.db_url)
create_all_tables(engine)

webcli_engine = WebCLIEngine(
    db_engine = engine,
    wsc_manager=WebSocketConnectionManager(),
    action_handlers = action_handlers
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
app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")
app.mount("/dist", StaticFiles(directory=os.path.join(WEB_DIR, "dist")), name="dist")
templates = Jinja2Templates(directory=os.path.join(WEB_DIR, "dist", "templates"))

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
    log_prefix = "home_page"
    logger.debug(f"{log_prefix}: enter")
    set_client_id = False
    client_id = request.cookies.get("client-id")
    if client_id is None:
        client_id = str(uuid.uuid4())
        logger.debug(f"f{log_prefix}: client-id cookie not found, generate one, it is {client_id}")
        set_client_id = True
    else:
        logger.debug(f"f{log_prefix}: client-id is {client_id}")

    ahcs = await webcli_engine.get_action_handler_configurations(client_id)
    config_map = {
        ahc.action_handler_name: ahc.model_dump(mode='json') for ahc in ahcs
    }
    response = templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Web CLI Demo",
            "client_id": client_id,
            "config_map": json.dumps(config_map),
            "websocket_uri": config.core.websocket_uri,
        }
    )
    if set_client_id:
        logger.debug(f"{log_prefix}: set client-id cookie to {client_id}")
        response.set_cookie(
            key="client-id",
            value=client_id,
            max_age=86400*365*10,   # cookie lasts 10 year
            path="/",               # optional: root path
            secure=False,           # optional: send only over HTTPS if True
            httponly=False,         # optional: not accessible via client-side JS
            samesite="strict",      # optional: 'strict' | 'lax' | 'none'
        )
        
    logger.debug(f"{log_prefix}: exit")
    return response
