#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

import os
import importlib
import uuid
import json
import datetime

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from contextlib import asynccontextmanager

from webcli2 import WebCLIEngine, WebCLIEngineStatus, WebSocketConnectionManager, UserManager
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

webcli_engine = WebCLIEngine(
    db_engine = engine,
    wsc_manager=WebSocketConnectionManager(),
    action_handlers = action_handlers
)
user_manager = UserManager(
    db_engine=engine, 
    private_key=config.core.private_key, 
    public_key=config.core.public_key
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
async def handle_action(request_data: dict, request:Request):
    log_prefix = "handle_action"
    logger.debug(f"{log_prefix}: enter")
    jwt_token = request.cookies.get("access-token")
    if jwt_token is None:
        # user is not logged in, send HTTP 403
        raise HTTPException(status_code=403, detail="Access denied")
    user = user_manager.get_user_from_jwt_token(jwt_token)
    if user is None:
        # The JWT token did not pass validation
        raise HTTPException(status_code=403, detail="Access denied")
    status, aciton = await webcli_engine.async_start_action(request_data, user)
    if status == WebCLIEngineStatus.OK:
        logger.debug(f"handle_action: exit")
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

    jwt_token = request.cookies.get("access-token")
    if jwt_token is None:
        # user is not logged in, redirect user to login page
        response = redirect("/login")
        logger.debug(f"{log_prefix}: JWT token not found, redirect user to login page")
        logger.debug(f"{log_prefix}: exit")
        return response
    
    logger.debug(f"{log_prefix}: JWT token found")
    user = user_manager.get_user_from_jwt_token(jwt_token)
    if user is None:
        response = redirect("/login")
        logger.debug(f"{log_prefix}: JWT token did not pass validation")
        logger.debug(f"{log_prefix}: exit")
        return response

    client_id = str(uuid.uuid4())
    user_id = user.id

    ahcs = await webcli_engine.get_action_handler_configurations(user_id)
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
    logger.debug(f"{log_prefix}: exit")
    return response

##########################################################
# Endpoint for login page
##########################################################
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    log_prefix = "login_page"
    logger.debug(f"{log_prefix}: enter")

    jwt_token = request.cookies.get("access-token")
    if jwt_token is not None:
        user = user_manager.get_user_from_jwt_token(jwt_token)
        if user is not None:
            response = redirect("/")
            logger.debug(f"{log_prefix}: JWT token found, redirect user to home page")
            logger.debug(f"{log_prefix}: exit")
            return response
    
    # either no JWT token or invalid JWT token
    response = templates.TemplateResponse(
        "login_page.html", 
        {
            "request": request, 
        }
    )
        
    logger.debug(f"{log_prefix}: exit")
    return response

@app.post("/login", response_class=HTMLResponse)
async def login_action(
    username: str = Form(...), 
    password: str = Form(...)
):
    log_prefix = "login_action"
    logger.debug(f"{log_prefix}: enter")

    user = user_manager.login(username, password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorret username or password")

    jwt_token = user_manager.create_jwt_token(user)
    response = redirect("/")
    response.set_cookie(
        key="access-token",
        value=jwt_token,
        max_age=86400*365*10,   # cookie lasts 10 year
        path="/",               # optional: root path
        secure=False,           # optional: send only over HTTPS if True
        httponly=False,         # optional: not accessible via client-side JS
        samesite="strict",      # optional: 'strict' | 'lax' | 'none'
    )
        
    logger.debug(f"{log_prefix}: exit")
    return response

def redirect(url):
    html_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
    <meta http-equiv="refresh" content="0;url={url}">
</head>
<body></body>
</html>
"""
    return HTMLResponse(content=html_content)
