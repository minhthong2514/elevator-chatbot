from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from engine import ElevatorAI
import uvicorn
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Khởi tạo bộ não AI (Sử dụng bản LangChain mới nhất)
brain = ElevatorAI()

class QueryRequest(BaseModel):
    question: str

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ask")
async def ask_elevator_stream(req: QueryRequest):
    # Lấy generator từ LangChain (rag_chain.stream)
    generator = brain.ask(req.question, stream=True)
    
    def generate():
        try:
            for chunk in generator:
                if chunk:
                    # LangChain thường trả về string, nhưng để chắc chắn ta ép kiểu
                    # Thêm \n\n theo chuẩn Server-Sent Events (SSE) nếu index.html của bạn dùng EventSource
                    yield str(chunk)
        except Exception as e:
            yield f"\n[Lỗi Stream]: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    # Chạy ở cổng 8081 như bạn đã thiết lập
    uvicorn.run(app, host="0.0.0.0", port=8081)