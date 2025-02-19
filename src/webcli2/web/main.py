#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logger = logging.getLogger(__name__)

from typing import List, Union, Optional
import os
import uuid

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel

from webcli2.service_loader import load_webcli_service
from webcli2.core.data import Thread, User, Action, ThreadAction, ObjectNotFound
    
from fastapi import WebSocket

from webcli2.config import load_config
from webcli2.core.service import InvalidJWTTOken, NoHandler
from .libs.tools import redirect

class PatchThreadActionRequest(BaseModel):
    show_question: Optional[bool] = None
    show_answer: Optional[bool] = None

class PatchActionRequest(BaseModel):
    title: str

class CreateThreadRequest(BaseModel):
    title: str
    description: str

class CreateActionRequest(BaseModel):
    title: str
    raw_text: str
    request: dict

class PatchThreadRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

##########################################################
# WEB_DIR is the directory of web insode webcli2 package
##########################################################
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

config = load_config()
service = load_webcli_service(config)

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
    
    try:
        user = service.get_user_from_jwt_token(jwt_token)
    except InvalidJWTTOken:
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
    service.startup()
    yield
    service.shutdown()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")
app.mount("/dist", StaticFiles(directory=os.path.join(WEB_DIR, "dist")), name="dist")
app.mount("/resources", StaticFiles(directory=config.core.resource_dir), name="resources")
templates = Jinja2Templates(directory=os.path.join(WEB_DIR, "dist", "templates"))

##########################################################
# Endpoint for websocket
##########################################################
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await service.websocket_endpoint(websocket)

##########################################################
# Endpoint for homepage
##########################################################
@app.get("/threads/{thread_id}", response_class=HTMLResponse, include_in_schema=False)
async def thread_page(request: Request, thread_id:int, user:Union[User, HTMLResponse]=Depends(authenticate_or_redirect)):
    if isinstance(user, HTMLResponse):
        return user

    client_id = str(uuid.uuid4())
    user_id = user.id

    response = templates.TemplateResponse(
        "thread_page.html", 
        {
            "request": request, 
            "title": f"Thread {thread_id}",
            "thread_id": thread_id,
            "client_id": client_id,
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
    user = service.login_user(email = username, password = password)
    if user is None:
        logger.info(f"do_login: Incorrect username and/or password")
        raise HTTPException(status_code=401, detail="Incorret username or password")

    jwt_token = service.generate_user_jwt_token(user)

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

@app.post("/logout", response_class=HTMLResponse, include_in_schema=False)
async def do_logout():
    response = redirect("/login")
    response.delete_cookie(key="access-token")
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
    return service.list_threads(user=user)

@app.post("/apis/threads", response_model=Thread)
async def create_thread(request:Request, create_thread_request:CreateThreadRequest, user:User=Depends(authenticate_or_deny)):
    return service.create_thread(
        title=create_thread_request.title, 
        description=create_thread_request.description, 
        user=user
    )

@app.delete("/apis/threads/{thread_id}")
async def delete_thread(request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        return service.delete_thread(thread_id, user=user)
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")

@app.get("/apis/threads/{thread_id}", response_model=Thread)
async def get_thread(request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        return service.get_thread(thread_id, user=user)
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")

@app.patch("/apis/threads/{thread_id}", response_model=Thread)
async def patch_thread(request_data: PatchThreadRequest, request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        return service.patch_thread(
            thread_id, 
            user=user, 
            title=request_data.title, 
            description=request_data.description
        )
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")

@app.post("/apis/threads/{thread_id}/actions", response_model=ThreadAction)
async def create_thread_action(request_data: CreateActionRequest, request:Request, thread_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        thread_action = service.create_thread_action(
            request=request_data.request, 
            thread_id=thread_id,
            title=request_data.title, 
            raw_text=request_data.raw_text, 
            user=user
        )
        return thread_action
    except NoHandler:
        raise HTTPException(status_code=400, detail="No handler is registered for the action you requested")
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")

@app.delete("/apis/threads/{thread_id}/actions/{action_id}")
async def remove_action_from_thread(request:Request, thread_id:int, action_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        service.remove_action_from_thread(action_id=action_id, thread_id=thread_id, user=user)
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")

@app.patch("/apis/threads/{thread_id}/actions/{action_id}", response_model=ThreadAction)
async def patch_thread_action(request_data: PatchThreadActionRequest, request:Request, thread_id:int, action_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        thread_action = service.patch_thread_action(
            thread_id, 
            action_id, 
            show_question=request_data.show_question, 
            show_answer=request_data.show_answer,
            user=user
        )
        return thread_action
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")

@app.patch("/apis/actions/{action_id}", response_model=Action)
async def patch_action(request_data: PatchActionRequest, request:Request, action_id:int, user:User=Depends(authenticate_or_deny)):
    try:
        action = service.patch_action(action_id=action_id, title = request_data.title, user=user)
        return action
    except ObjectNotFound:
        raise HTTPException(status_code=404, detail="Object not found")
