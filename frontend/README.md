# 디렉토리
Node_Review_App/
├── .venv/..           <!-- 파이쎤 가상 환경 패키지 -->
├── node_modules/..    <!-- node.js 패키지 -->
├── public/            <!-- 프론트엔드 -->
│   ├── main.html
│   └── sub.html
├── utils/             <!-- 크롤링, 모델 예측, LLM 모듈 -->
│   └── app.py         <!-- 파이썬 API 서버 -->
├── package.json
└── server.js           <!-- Node.js 백엔드 API 서버 공간 -->

# API(node.js server <-> python API server)
{
    "product_name" : 상품명,        <!-- 추가 고려 -->
    "product_image" : 상품 이미지,   <!-- 추가 고려 -->
    "pos": [
        "긍정 문장1",
        "긍정 문장2",
        "긍정 문장3"
    ],
    "neu": [
        "중립 문장1",
        "중립 문장2",
        "중립 문장3"
    ],
    "neg": [
        "부정 문장1",
        "부정 문장2",
        "부정 문장3"
    ],
    "final_summary": "전체 요약 문장",
    "average_rate": 0,              <!-- 상품 평균 평점 -->
    "total_score": 0,               <!-- 추천도 긍정 비율 -->
    "top_aspect_score": {           <!-- 대표 긍정 -->
        <!-- "대표 긍정 속성" : 비율 -->
        "aspect1": 0,
        "aspect2": 0
    },
    "bottom_aspect_score" : {        <!-- 대표 부정 -->
        <!-- "대표 부정 속성" : 비율 -->
        "aspect3": 0,
        "aspect4": 0
    }
}

# Run
- main -> 로딩(API -> 크롤링 -> 모델 예측 -> LLM) -> sub
- 실행 순서 : app.py -> server.js
- .venv 종료 :deactivate
- 서버 : npm run dev:mac, win

# 추가 예정
- sub.html 상단 : 상품명, 사진 블록 추가, 상품 URL