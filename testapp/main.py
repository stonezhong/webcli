#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

app = FastAPI() # 定义一个fast API application
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="static/js-bundle")

@app.get("/")
async def root():
    return {"message": "Hello world!"}

@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    # Render the 'index.html' template with some context
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "title": "Home Page"
        }
    )
