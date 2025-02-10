#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

from typing import List, Union, Optional, Dict
import os
import importlib
import uuid
import json

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from contextlib import asynccontextmanager

from webcli2 import WebCLIEngine, WebCLIEngineStatus, WebSocketConnectionManager, UserManager
from webcli2.models import Thread, User, Action, ThreadAction
from webcli2.models.apis import CreateThreadRequest, CreateActionRequest, PatchActionRequest, \
    PatchThreadActionRequest, PatchThreadRequest
from fastapi import WebSocket

from webcli2.config import load_config, ActionHandlerInfo
from .libs.tools import redirect

##########################################################
# WEB_DIR is the directory of web insode webcli2 package
##########################################################
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

config = load_config()

##########################################################
# Loading all action handlers
# We will install ConfigHandler anyway
##########################################################
action_handlers = {
}

def config_action_handlers():
    action_handlers_config:Dict[str, ActionHandlerInfo] = {
        "config": ActionHandlerInfo(
            module_name="webcli2.action_handlers.config",
            class_name="ConfigHandler",
            config = {}
        )
    }
    action_handlers_config.update(config.core.action_handlers)
    for action_handler_name, action_handler_info in action_handlers_config.items():
        logger.info(f"Loading action handler: name={action_handler_name}, module={action_handler_info.module_name}, class={action_handler_info.class_name}")
        module = importlib.import_module(action_handler_info.module_name)
        klass = getattr(module, action_handler_info.class_name)
        action_handler = klass(**action_handler_info.config)
        action_handlers[action_handler_name] = action_handler
    logger.info(f"All action handlers are loaded")
config_action_handlers()

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
# Authenticate user
# If user is authenticated, it returns a User object
# Otherwise, it returns None
##########################################################
def authenticate_user(request:Request) -> Optional[User]:
    jwt_token = request.cookies.get("access-token")
    if jwt_token is None:
        logger.info(f"authenticate_user: {request.url}, missing cookie access-token for JWT token")
        return None

    user = user_manager.get_user_from_jwt_token(jwt_token)
    if user is None:
        # The JWT token did not pass validation
        logger.info(f"authenticate_user: {request}, invalid JWT token")
        return None

    return user

##########################################################
# Authenticate user from JWT token or deny
##########################################################
def authenticate_or_deny(request:Request) -> User:
    user = authenticate_user(request)
    if user is None:
        logger.info(f"authenticate_or_deny: {request.url}, user not authenticated, access denied")
        raise HTTPException(status_code=403, detail="Access denied")
    return user

##########################################################
# Authenticate user from JWT token or redirect to login page
##########################################################
def authenticate_or_redirect(request:Request) -> Union[User, HTMLResponse]:
    user = authenticate_user(request)
    if user is None:
        # user is not logged in, redirect user to login page
        response = redirect("/login")
        logger.info(f"authenticate_or_redirect: {request.url}, user not authenticated, redirect to login page")
        return response   
    return user

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
# Endpoint for websocket
##########################################################
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await webcli_engine.wsc_manager.websocket_endpoint(websocket)

##########################################################
# Endpoint for homepage
##########################################################
@app.get("/threads/{thread_id}", response_class=HTMLResponse, include_in_schema=False)
async def thread_page(request: Request, thread_id:int, user:Union[User, HTMLResponse]=Depends(authenticate_or_redirect)):
    if isinstance(user, HTMLResponse):
        return user

    client_id = str(uuid.uuid4())
    user_id = user.id

    ahcs = await webcli_engine.get_action_handler_configurations(user_id)
    config_map = {
        ahc.action_handler_name: ahc.model_dump(mode='json') for ahc in ahcs
    }
    response = templates.TemplateResponse(
        "thread_page.html", 
        {
            "request": request, 
            "title": "Web CLI Demo",
            "thread_id": thread_id,
            "client_id": client_id,
            "config_map": json.dumps(config_map),
            "websocket_uri": config.core.websocket_uri,
        }
    )       
    return response

##########################################################
# Endpoint for thread list page
##########################################################
@app.get("/threads", response_class=HTMLResponse, include_in_schema=False)
async def threads_page(request: Request, user:Union[User, HTMLResponse]=Depends(authenticate_or_redirect)):
    if isinstance(user, HTMLResponse):
        return user

    response = templates.TemplateResponse(
        "threads_page.html", 
        {
            "request": request, 
        }
    )       
    return response

##########################################################
# Endpoint for login page
##########################################################
@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, user:Optional[User]=Depends(authenticate_user)):
    if user is not None:
        response = redirect("/threads")
        logger.info(f"login_page: User already authenticated, redirect to threads page")
        return response
    
    # either no JWT token or invalid JWT token
    response = templates.TemplateResponse(
        "login_page.html", 
        {
            "request": request, 
        }
    )
    return response

@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
async def do_login(
    username: str = Form(...), 
    password: str = Form(...)
):
    user = user_manager.login(username, password)
    if user is None:
        logger.info(f"do_login: Incorrect username and/or password")
        raise HTTPException(status_code=401, detail="Incorret username or password")

    jwt_token = user_manager.create_jwt_token(user)
    logger.info(f"do_login: User {username} logged in")
    response = redirect("/threads")
    response.set_cookie(
        key="access-token",
        value=jwt_token,
        max_age=86400*365*10,   # cookie lasts 10 year
        path="/",               # optional: root path
        secure=False,           # optional: send only over HTTPS if True
        httponly=False,         # optional: not accessible via client-side JS
        samesite="strict",      # optional: 'strict' | 'lax' | 'none'
    )
        
    return response

##########################################################
# Endpoint for homepage
##########################################################
@app.get("/test", response_class=HTMLResponse, include_in_schema=False)
async def test_page(request: Request):
    response = templates.TemplateResponse(
        "test_page.html", 
        {
            "request": request, 
        }
    )       
    return response

##########################################################
# REST APIs
##########################################################

##########################################################
# Thread management
##########################################################
@app.get("/apis/threads", response_model=List[Thread])
async def list_threads(request:Request, user:User=Depends(authenticate_or_deny)):
    threads = await webcli_engine.list_threads(user)
    return threads

@app.post("/apis/threads", response_model=Thread)
async def create_thread(request:Request, create_thread_request:CreateThreadRequest, user:User=Depends(authenticate_or_deny)):
    thread = await webcli_engine.create_thread(create_thread_request, user)
    return thread

@app.delete("/apis/threads/{thread_id}")
async def delete_thread(request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    await webcli_engine.delete_thread(thread_id)
    return None

@app.get("/apis/threads/{thread_id}", response_model=Thread)
async def get_thread(request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    thread = await webcli_engine.get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

@app.patch("/apis/threads/{thread_id}", response_model=Thread)
async def patch_thread(request_data: PatchThreadRequest, request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    thread = await webcli_engine.patch_thread(thread_id, request_data)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

@app.post("/apis/threads/{thread_id}/actions", response_model=ThreadAction)
async def create_thread_action(request_data: CreateActionRequest, request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    status, thread_aciton = await webcli_engine.async_start_action(request_data, user, thread_id)
    if status == WebCLIEngineStatus.OK:
        return thread_aciton
    if status == WebCLIEngineStatus.NO_HANDLER:
        raise HTTPException(status_code=400, detail="No handler is registered for the action you requested")
    else:
        raise HTTPException(status_code=500, detail=f"Internal server error, status = {status}")

@app.delete("/apis/threads/{thread_id}/actions/{action_id}")
async def remove_action_from_thread(request:Request, thread_id:int, action_id:int, user:User=Depends(authenticate_or_deny)):
    await webcli_engine.remove_action_from_thread(thread_id, action_id)
    return None

@app.patch("/apis/threads/{thread_id}/actions/{action_id}", response_model=ThreadAction)
async def patch_thread_action(request_data: PatchThreadActionRequest, request:Request, thread_id:int, action_id:int, user:User=Depends(authenticate_or_deny)):
    thread_action = await webcli_engine.patch_thread_action(thread_id, action_id, request_data)
    if thread_action is None:
        raise HTTPException(status_code=404, detail="ThreadAction not found")
    return thread_action

@app.patch("/apis/actions/{action_id}", response_model=Action)
async def patch_action(request_data: PatchActionRequest, request:Request, action_id:int, user:User=Depends(authenticate_or_deny)):
    action = await webcli_engine.patch_action(action_id, request_data)
    if action is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return action
