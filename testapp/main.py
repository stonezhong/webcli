#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine

app = FastAPI() # 定义一个fast API application
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dist", StaticFiles(directory="dist"), name="dist")

templates = Jinja2Templates(directory="dist/templates")

@app.get("/test")
async def test():
    return {
        "ui_type": "message",
        "message": "Hello world!"
    }

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Home Page"
        }
    )



################################################################################################
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from asyncio import Event, get_event_loop, AbstractEventLoop
from pydantic import BaseModel
import traceback 

from webcli2 import CLIHandler, AsyncActionOpStatus
from webcli2.db_models import create_all_tables
import json

class CreateRequest(BaseModel):
    pass

class UpdateRequest(BaseModel):
    status: str

engine = create_engine("sqlite:////home/stonezhong/DATA_DISK/projects/webcli/testapp/foo.db")
create_all_tables(engine)
cli_handler = CLIHandler(db_engine = engine, debug=True)


@app.on_event("startup")
async def startup_event():
    cli_handler.startup()

@app.on_event("shutdown")
async def startup_shutdown():
    cli_handler.shutdown()

# create an async action
@app.post("/actions")
async def create(request: CreateRequest):
    op_status, async_action = await cli_handler.async_start_async_action(json.loads(request.model_dump_json()))
    return {
        "id": async_action.id
    }

# monitor an async action
@app.get("/actions/{id}/monitor")
async def monitor(id:int):
    op_status, async_action = await cli_handler.async_wait_for_update_async_action(id, 15)
    if op_status == AsyncActionOpStatus.NOT_FOUND:
        return {
            "message": f"action with {id} does not exist",
        }

    if op_status == AsyncActionOpStatus.ACTION_COMPLETED:
        return {
            "message": f"action with {id} is already completed",
        }

    if op_status == AsyncActionOpStatus.TIMEDOUT:
        return {
            "message": f"query timed out",
        }

    assert  async_action is not None

    if async_action.is_completed:
        return {
            "response": async_action.response,
        }
    else:
        return {
            "status": async_action.progress,
        }

# update an async action
@app.post("/actions/{id}/update")
async def change(id:int, request:UpdateRequest):
    op_status = await cli_handler.async_update_progress_async_action(id, {"status": request.status})

    if op_status == AsyncActionOpStatus.NOT_FOUND:
        return {
            "message": f"action with {id} does not exist",
        }

    if op_status == AsyncActionOpStatus.ACTION_COMPLETED:
        return {
            "message": f"action with {id} is already completed",
        }

    assert op_status == AsyncActionOpStatus.OK
    return {
        "message": f"action with {id} is updated"
    }


# complete an async action
@app.post("/actions/{id}/complete")
async def complete(id:int, request:UpdateRequest):
    op_status = await cli_handler.async_complete_progress_async_action(id, {"status": request.status})

    if op_status == AsyncActionOpStatus.NOT_FOUND:
        return {
            "message": f"action with {id} does not exist",
        }

    if op_status == AsyncActionOpStatus.ACTION_COMPLETED:
        return {
            "message": f"action with {id} is already completed",
        }

    assert op_status == AsyncActionOpStatus.OK
    return {
        "message": f"action with {id} is completed"
    }

