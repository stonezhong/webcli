#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

app = FastAPI() # 定义一个fast API application
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dist", StaticFiles(directory="dist"), name="dist")

templates = Jinja2Templates(directory="dist/templates")

# @app.get("/")
# async def root():
#     return {"message": "Hello world!"}

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Home Page"
        }
    )

