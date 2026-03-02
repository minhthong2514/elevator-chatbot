from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from engine import ElevatorAI
import uvicorn
import json
import asyncio
from transformers import TextIteratorStreamer
from threading import Thread

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Khởi tạo bộ não AI (Giữ nguyên engine.py của bạn)
brain = ElevatorAI()

class QueryRequest(BaseModel):
    question: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ask")
async def ask_elevator_stream(req: QueryRequest):
    # Lấy streamer từ hàm ask của bạn
    generator = brain.ask(req.question, stream=True)
    
    # Hàm bao để FastAPI yield dữ liệu ra stream
    def generate():
        for new_text in generator:
            if new_text:
                yield new_text

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)