# absa-review-summary-service

본 프로젝트는 소비자가 수많은 리뷰를 모두 확인하기 어렵다는 한계에서 출발했습니다. 이를 위해 별점 별 리뷰를 균형있게 추출하고 속성 기반 감정 분석을 진행하여, 최종적으로 사용자의 구매 판단을 돕는 유용한 정보를 제공하고자 합니다.

## 기술 스택
| 구분 | 기술 |
|------|------|
| Frontend | HTML, Tailwind CSS |
| Node.js 서버 | Express.js |
| Python 서버 | FastAPI, uvicorn |
| 크롤링 | Playwright |
| 감성 분석 모델 | KoELECTRA 기반 ABSA 모델 |
| 요약 생성 | Google Gemini API |
| 실시간 통신 | SSE (Server-Sent Events) |

## 프로젝트 구조
```
├── backend/
│   ├── main.py               # FastAPI 앱, lifespan, 엔드포인트
│   ├── service.py            # 오케스트레이터
│   ├── crawler.py            # 리뷰 크롤링 (Playwright)
│   ├── inference.py          # 모델 생성 및 추론
│   ├── classifier.py         # 감성 분류, 대표 문장 선정
│   ├── analyzer.py           # 통계 계산, 요약 생성
│   ├── aggregator.py         # 최종 결과 조립
│   ├── requirements.txt      # 필요 외부 패키지 관리
│   └── .gitignore
├── frontend/
│   ├── public/
│       ├── main.html         # 메인 페이지
│       └── sub.html          # 결과 페이지
│   ├── server.js             # Node.js Express 서버
│   ├── package.json
│   ├── package-lock.json
│   ├── .gitignore
│   └── README.md
├── model/
│   ├── checkpoints/          # 모델 학습 중 가중치 저장 디렉토리
│       └── .gitkeep
│   ├── dataset/
│       ├── __init__.py
│       └── make_dataset.py   # 학습 데이터셋 생성
│   ├── datasets/             # 학습 데이터 저장 디렉토리
│       └── Aspect.csv        # 속성
│   ├── model/
│       ├── __init__.py
│       ├── make_model.py     # 모델 생성
│       └── training.py       # 모델 학습
│   ├── models/               # 모델 가중치 저장 디렉토리
│       └── .gitkeep 
│   ├── utils/
│       ├── __init__.py 
│       ├── config.py         # 설정 정보 로드
│       └── metrics.py        # 모델 평가
│   ├── config.yaml           # 설정 정보
│   ├── review_model.ipynb    # 모델 작업 (구)
│   ├── reveiw_modelV3.ipynb  # 모델 작업 (신)
│   └── .gitignore
├── LICENSE
└── README.md
```

## 설치 및 실행

### 요구 사항

- Python 3.10+
- Node.js 18+
- Microsoft Windows

> [!WARNING]
> macOS 환경의 경우, Mecab 설치 및 GPU 가속 설정 단계에서 문제가 발생할 수 있습니다.

### 환경 변수

`backend/` 디렉토리에 `.env` 파일이 필요합니다.
 
```
GEMINI_API_KEY=your_api_key
```

### Python 패키지 설치
```bash
pip install -r requirements.txt
```

### Node.js 패키지 설치
```bash
npm install
```

### 실행
```bash
# Python 서버 (포트 8000)
cd backend
python main.py

# Node.js 서버 (포트 5001)
cd frontend
node server.js
```

브라우저에서 'http://localhost:5001' 접속

## 지원 항목

11번가에서 판매 중인 IT기기(컴퓨터, 휴대폰, 카메라, 게임기, 태블릿, 자동차기기)에 대해 지원합니다.

## 모델 가중치

서버 시작 시 model/models 디렉토리에 가중치 파일이 없으면 Google Drive에서 자동으로 다운로드됩니다.

## 학습 데이터

본 프로젝트는 AI Hub에서 제공하는 [속성 기반 감정 분석 데이터](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71603)를 활용하였습니다.
해당 데이터는 AI Hub의 이용정책에 따라, 승인받지 않은 제3자에게 열람, 제공, 양도, 대여 및 판매하는 것이 금지되어있습니다.

## 팀원
선문대학교 컴퓨터공학부 기계학습프로젝트 12분반 5조
| 이름 | 역할 | GitHub |
| :---: | :---: | :---: |
| **박영진** | 팀장 / 모델 설계 | [@yungjin702](https://github.com/yungjin702) |
| **윤홍규** | 팀원 / 프론트엔드 | [@ghdrb1246](https://github.com/ghdrb1246) |
| **전세호** | 팀원 / 백엔드 | [@Jeon-Seho](https://github.com/Jeon-Seho) |
| **차무관** | 팀원 / 데이터 전처리, 백엔드 보조 | [@ChaMooKwan](https://github.com/ChaMooKwan) |