# 메인

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import service

import uvicorn
import os
import json
from pathlib import Path
import gdown
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from google import genai

from inference import init_model

def download_model_weight():
    ROOT_DIR = Path(__file__).resolve().parent.parent
    model_path = ROOT_DIR / "model" / "models" / "final_review_classifier_modelV3(KoElectra).pt"
    
    if not os.path.exists(model_path):
        print("---------- 모델 가중치 다운로드 시작 ----------")
        FILE_ID = "1qEpGCKx7XxWs19RqBqIWdDH7vP9a2rBj"
        gdown.download(f"https://drive.google.com/uc?id={FILE_ID}", model_path, quiet=False)
        print("---------- 모델 가중치 다운로드 완료 ----------\n")
    else:
        print("---------- 모델 가중치 존재 ----------")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행
    load_dotenv()
    download_model_weight()
    
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
    async def event_stream():
        try:
            async for event in service.run(
                req.url,
                device=request.app.state.device,
                infer_model=request.app.state.infer_model,
                tokenizer=request.app.state.tokenizer,
                embed_model=request.app.state.embed_model,
                gemini_client=request.app.state.gemini_client
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            # raise HTTPException(status_code=500, detail=str(e))
            yield f"data: {json.dumps({'step': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"
        
    return StreamingResponse(event_stream(), media_type="text/event-stream")
    
if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8000
    )