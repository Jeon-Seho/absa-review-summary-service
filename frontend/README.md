# 1. 디렉토리
```
absa-review-summary-service/
├── .venv/..                    <!-- 파이쎤 가상 환경 패키지(필수x) -->
├── node_modules/..             <!-- node.js 패키지 -->
├── backend/                    <!-- 백엔드 -->          
│   └── app.py                  <!-- 크롤링, 모델 예측, LLM 모듈, API 서버 -->
├── frontend/                   <!-- 프론트엔드 -->  
│   ├──── public/           
│   │     ├── main.html         <!-- 링크 입력 -->
│   │     └── sub.html          <!-- 결과 출력 -->
│   └── server.js               <!-- Node.js 서버 -->
├─── package.json
...
```

# 2. API JSON(node.js server <-> python API server)
```
{
  "success": true,                      <!-- 성공/실패 여부 -->
  "data": {
    "product_name": "상품명",             <!-- 크롤링된 상품명 -->
    "average_rate": 0.0,                <!-- 상품 평균 평점 -->
    "total_score": 0,                   <!-- 추천도 긍정 비율 -->
    "final_summary": "전체 요약 문장",     <!-- LLM으로 요약된 200길이의 문장 -->
    "pos": [                            <!-- 긍정 문자 3개 -->
        "긍정 문장1",
        "긍정 문장2",
        "긍정 문장3"
    ],
    "neu": [                            <!-- 중립 문자 3개 -->
        "중립 문장1",
        "중립 문장2",
        "중립 문장3"
    ],
    "neg": [                            <!-- 부정 문자 3개 -->
        "부정 문장1",
        "부정 문장2",
        "부정 문장3"
    ],
    "top_aspect_score": {               <!-- 대표 긍정 -->
        <!-- "대표 긍정 속성" : 비율 -->
        "aspect1": 0,
        "aspect2": 0
    },
    "bottom_aspect_score": {            <!-- 대표 부정 -->
        <!-- "대표 부정 속성" : 비율 -->
        "aspect3": 0,
        "aspect4": 0
    }
  }
}
```

# 3. 실패 시 반환되는 JSON 구조 (success: false)
## 3.1 입력 주소가 비어있거나 형식 오류일 때 (400 Error)
```
{
  "success": false,
  "error": "URL이 누락되었습니다."
}
```

## 3.2 파이썬 크롤링 / 모델 / LLM 모듈에서 예외가 발생했을 때 (500 Error)
```
{
  "success": false,
  "error": "파이썬 AI 모델 내부 연산 실패"
}
```

## 3.3 파이썬 서버(8000포트)가 꺼져있어 Node.js가 접근하지 못할 때 (500 Error)
```
{
  "success": false,
  "error": "파이썬 AI 서버가 응답하지 않습니다."
}
```

# 4. Run
- 실행 순서는 파이썬 서버, node 서버로 이다. 이유는 파이썬 서버가 먼저 실행되어야 node 서버에서 모델을 인식할 수 있기 때문
- npm 명령어로 실행했을 경우
    - npm run dev:mac or win를 실행 후 우선 main.py이 시작된다.
    - main.py에서 모델 준비가 완료되면, API 서버를 시작하고, http://localhost:8000으로 현재 서버가 정상 작동 상태 여부를 확인한다.
    - 이에 따라 server.js 실행 / 대기 상태 or 405 Error 
## 4.1 작동 순서
- main.html -> 로딩 -> main.py(API -> 크롤링 -> 모델 예측 -> LLM -> API) sub.html

## 4.2 실행 순서
### 4.2.1 수동 실행
- python main.py 실행 후 node server.js 실행

### 4.2.2 자동 실행
#### 4.2.2.1 mac(.venv)
- npm run dev:mac

#### 4.2.2.1 win(로컬 or .venv)
- npm run dev:win
- npm run dev:winv

# 업데이트 내역
- 수동, 자동 실행 환경 구축 -> concurrently를 사용하고, main.py 부터 server.js 순으로 실행이 되어야함으로 wait-on를 사용 
- 상단에 상품명 크롤링으로 표시, 이미지는 링크에서 상품 id로 이미지 조회 후 표시
- sub 폼에서 이전 데이터가 남아 있는 항상 -> 링크를 입력하지 않고, 주소창에 바로 sub 폼으로 이동하면 이전 리뷰 분석한 내용이 그대로 남아 있음.
- 로딩창에서 진행 사항을 알 수 없음 -> 크롤링, 모델 예측/분석, LLM 요약까지 하는데 시간이 많이 듬.
- 안내 스타일 수정이 필요함 -> 성공은 폼으로 넘어가는 것으로 하고, 경고, 에러와 같은 내용을 안내 한다. SweetAlert2와 같은 알림창으로 스타일 수정.

# 추가 및 수정 사항
1. main.html(알림)
- 12 :        sweetalert2 인포트
- 34 ~ 48 :   sweetalert2 알림창 스타일 정의
- 161 ~ 164 : 공통 함수 정의
- 183 ~ 184 : "상품 링크를 입력해 주세요!" 알림창 변경
- 230 ~ 240 : "분석에 실패했습니다." 알림창 변경
- 248 ~ 257 : "통신 장애가 발생했습니다." 알림창 변경

2. sub.html(상단 상품명, 이미지, 강제 접근에 대한 경고 알림)
- 19 ~ 25   : sub 폼에서 버벅임이 발생하면 .glass-panel 부분을 제거
- 49        : div 태크에 id="normal_dashboard_view" 추가
- 66 ~ 93   : 상품명, 이지미, 상품 링크 추가
- 176 ~ 194 : sub.htil 강제 접근에 대한 경고 알림 폼
- 206 ~ 216 : 경고 알림 폼 출력
- 228 ~ 268 : 상품명, 이미지, 링크 폼에 추가

3. main.py
- 52 ~ 54 : wait-on 라이브러리가 파이썬 서버의 작동을 확인하고 Node.js를 켜줄 수 있도록 응답을 줌