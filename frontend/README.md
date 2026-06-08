# 1. 디렉토리
```
absa-review-summary-service/
...
├── frontend/
│   ├── public/
│   │   ├── main.html         # 메인 페이지
│   │   └── sub.html          # 결과 페이지 
│   ├── server.js             # Node.js Express 서버
│   ├── package.json          # npm에 의존하는 패키지의 리스트
│   ├── package-lock.json     # npm 패키지 매니저에서 node_modules에 설치된 패키지들
│   ├── .gitignore
│   └── README.md             # 프론트엔드 설명
...
```

# 2 메시지 규격
## 2.1 진행 중 (SSE 스트림)
 
```json
{ "step": "크롤링 중", "data": null }
{ "step": "추론 중",   "data": null }
{ "step": "분류 중",   "data": null }
{ "step": "분석 중",   "data": null }
```

## 2.2 완료 시 반환되는 JSON 구조
```json
{
  "step": "완료",                                           /* SSE 스트림 완료 여부 */
  "data": {
    "product_name": "갤럭시북"                               /* 사용자가 입력한 URL에 대한 상품명 */
    "average_rate": 4.8,                                   /* 상품 평균 평점 */
    "pos": ["대표 문장 1", "대표 문장 2", "대표 문장 3"],         /* 긍정 문자 3개 */
    "neu": ["..."],                                        /* 중립 문자 3개 */
    "neg": ["..."],                                        /* 부정 문자 3개 */
    "total_score": 0.82,                                   /* 추천도 긍정 비율 */
    "top_aspect_score": { "가격": 0.91, "디자인": 0.88 },     /* 대표 속성 긍정 비율 */
    "bottom_aspect_score": { "배터리": 0.61, "소음": 0.58 },  /* 대표 속성 부정 비율*/
    "final_summary": "요약 텍스트"                            /* LLM 상품 요약 문장 */
  }
}
```

## 2.3 에러 발생 시 반환되는 JSON 구조 (step: "error")
```json
{ "step": "error", "data": "에러 메시지" }
```

# 3. Run
- 실행 순서는 파이썬 서버, node 서버로 이다. 이유는 파이썬 서버가 먼저 실행되어야 node 서버에서 모델을 인식할 수 있기 때문
- npm 명령어로 실행했을 경우
    - npm run dev:mac or win를 실행 후 우선 main.py이 시작된다.
    - main.py에서 모델 준비가 완료되면, API 서버를 시작하고, http://localhost:8000으로 현재 서버가 정상 작동 상태 여부를 확인한다.
    - 이에 따라 server.js 실행 / 대기 상태 or 405 Error 

## 3.1 작동 순서
- main.html -> 로딩(API -> 크롤링 -> 모델 예측 -> LLM -> API) -> sub.html

## 3.2 실행 순서
### 3.2.1 수동 실행
- python main.py 실행 후 node server.js 실행

### 3.2.2 자동 실행
#### 3.2.2.1 mac(.venv)
- npm run dev:mac

#### 3.2.2.1 win(로컬 or .venv)
- npm run dev:win
- npm run dev:winv