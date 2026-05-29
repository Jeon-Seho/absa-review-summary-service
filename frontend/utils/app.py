# python_ai_server/app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI()

# Node.js로부터 받을 데이터 규격 정의 (상품 URL)
class AnalyzeRequest(BaseModel):
    url: str

# 크롤링 + ML 모델 + LLM 통합 파이프라인 함수
async def analyze_product_review_pipeline(url: str):
    print(f"[Python] 파이프라인 가동 -> URL: {url}")
    
    # 크롤링 (Playwright, BeautifulSoup 등)
    await asyncio.sleep(1.2) 
    
    # 정량 감성 ML 모델 예측 (KoBERT, PyTorch 등)
    await asyncio.sleep(1.0)
    model_metrics = {
        "average_rate": 3.8,
        "total_score": 92,
        "top_aspect_score": { "디자인 만족도": 98, "배터리 성능": 94 },
        "bottom_aspect_score" : { "가격 가성비": 48, "앱 사용 편의성": 65 }
    }
    
    # 생성형 LLM 요약 (OpenAI API, Ollama 등)
    await asyncio.sleep(1.3)
    llm_texts = {
        "pos": [
            "디자인이 매우 세련되었고 다크 Teal 톤의 마감이 훌륭합니다.",
            "배터리 수명이 타사 대비 30% 이상 길어 효율적입니다.",
            "화면 주사율이 높아 스크롤할 때의 조작감이 부드럽습니다."
        ],
        "neu": [
            "무게는 이전 세대 모델과 비교했을 때 큰 차이가 느껴지지 않습니다.",
            "충전 케이블 길이가 다소 짧은 편이나 사용에 지장은 없습니다."
        ],
        "neg": [
            "초기 다크 모드 및 환경 설정 진입 장벽이 다소 있습니다.",
            "기능이 고도화되어 제품 무게가 생각보다 묵직하게 체감됩니다."
        ],
        "final_summary": "이 제품은 디자인과 성능 면에서 압도적인 긍정 평가를 받고 있습니다. 특히 실구매자들은 뛰어난 가성비를 가장 큰 구매 결정 요인으로 꼽았습니다. 무게에 민감하지 않고 초기 설정의 번거로움을 감수할 수 있는 사용자라면, 동급 가격대에서 가장 후회 없는 선택이 될 것입니다."
    }; 
    
    # 두 딕셔너리를 하나로 결합하여 최종 결과 도출
    final_result = {**llm_texts, **model_metrics}
    return final_result

# wait-on 라이브러리가 파이썬 서버의 생존을 확인하고 Node.js를 켜줄 수 있도록 응답을 줍니다.
@app.api_route("/", methods=["GET", "HEAD"])
async def root_check():
    return {"status": "healthy", "message": "Python Server is running"}

# Node.js가 호출할 API 엔드포인트 정의
@app.post("/analyze")
async def predict_reviews(request: AnalyzeRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL이 없습니다.")
    
    try :
        # 파이프라인 함수를 실행하고 완료될 때까지 기다림(await)
        result = await analyze_product_review_pipeline(request.url)

        # 최종 JSON 출력
        return {"success": True, "data": result}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Node.js(5001포트)와 충돌나지 않게 8000번 포트로 구동
    uvicorn.run(app, host="127.0.0.1", port=8000)