#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request

app = FastAPI() # 定义一个fast API application

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root():
    return {"message": "Hello world!"}

@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    # Render the 'index.html' template with some context
    return templates.TemplateResponse(
        "test.html", 
        {
            "request": request, 
            "title": "Home Page"
        }
    )
