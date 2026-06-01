# 메인

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sentence_transformers import SentenceTransformer
from pathlib import Path
from dotenv import load_dotenv
from google import genai

import uvicorn
import os
import json
import gdown
import logging

import inference
import service

# 모델 가중치 다운로드
def download_model_weight(logger: logging.Logger):
    ROOT_DIR = Path(__file__).resolve().parent.parent
    model_path = ROOT_DIR / "model" / "models" / "final_review_classifier_modelV3(KoElectra).pt"
    
    if not os.path.exists(model_path):
        logger.warning("모델 가중치가 존재하지 않습니다.")
        logger.info("모델 가중치 다운로드를 시작합니다.")
        FILE_ID = "1qEpGCKx7XxWs19RqBqIWdDH7vP9a2rBj"
        gdown.download(f"https://drive.google.com/uc?id={FILE_ID}", str(model_path), quiet=False)
        logger.info("모델 가중치 다운로드를 완료했습니다.")
    else:
        logger.info("모델 가중치가 존재합니다.")
        

# Logger 생성
def setup_logger() -> logging.Logger:
    logger = logging.getLogger("logger")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    
    return logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 실행
    load_dotenv()
    logger = setup_logger()
    download_model_weight(logger)
    
    logger.info("lifespan: 모델 로딩을 시작합니다.")
    app.state.device, app.state.infer_model, app.state.tokenizer = inference.init_model()
    logger.info("lifespan: 모델 로딩을 완료했습니다.")
    
    logger.info("lifespan: 임베드 모델 로딩을 시작합니다.")
    app.state.embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    logger.info("lifespan: 임베드 모델 로딩을 완료했습니다.")
    
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

# 서버 활성화 확인 엔드포인트
@app.api_route("/", methods=["GET", "HEAD"])
async def root_check():
    return {"status": "healthy", "message": "Python Server is running"}

# 로직 엔드포인트
@app.post("/analyze")
async def analyze(req: AnalyzeRequest, request: Request):
    logger = logging.getLogger("logger")
    
    logger.info(f"프론트엔드 요청 수신: {req.url}")
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
            logger.warning(f"오류 발생: {str(e)}")
            yield f"data: {json.dumps({'step': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"
        
    return StreamingResponse(event_stream(), media_type="text/event-stream")
    
if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8000
    )