# 메인

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import service

import uvicorn
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from google import genai

from inference import init_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행
    load_dotenv()
    
    print("---------- lifespan: 모델 로딩 시작 ----------")
    app.state.device, app.state.infer_model, app.state.tokenizer = init_model()
    print("---------- lifespan: 모델 로딩 완료 ----------\n")
    
    print("---------- lifespan: 임베드 모델 로딩 시작 ----------")
    app.state.embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    print("----------lifespan: 임베드 모델 로딩 완료 ----------\n")
    
    app.state.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    app.state.gemini_client.models.generate_content_stream(
        model="gemini-3.1-flash-lite",
        contents="API 연결 시도 목적 더미 메시지",
    )

    yield
    # 서버 종료 시 실행

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5001"],    # 프론트엔드 포트
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str

@app.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    try:
        result = await service.run(
            req.url,
            device=request.app.state.device,
            infer_model=request.app.state.infer_model,
            tokenizer=request.app.state.tokenizer,
            embed_model=request.app.state.embed_model,
            gemini_client=request.app.state.gemini_client
        )
        
        return {"success": True, "data": result}
    except Exception as e:
        print("endpoint 에러 발생", e)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8000
    )