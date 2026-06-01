import express from 'express';
import cors from 'cors';
import { resolve as _resolve, join } from 'path';
import axios from 'axios';

const app = express();
const PORT = 5001;
const __dirname = _resolve();

// 프론트엔드와 백엔드 분리 시 도메인/포트가 다르므로 CORS 허용 필수
app.use(cors());

// JSON 형식의 요청 본문(Body)을 파싱하기 위한 미들웨어
app.use(express.json());

// public 폴더 내부의 HTML, CSS, JS 파일들을 브라우저에 정적으로 제공
app.use(express.static(join(__dirname, 'frontend/public')));

// ==============================================================================
// main
// ==============================================================================

// 단일 파이프라인 함수를 호출하는 비동기 API 엔드포인트
app.post('/api/analyze', async (req, res) => {
    const { product_url } = req.body;
    
    if (!product_url) {
        return res.status(400).json({ success: false, error: "URL이 누락되었습니다." });
    }
    try {
        console.log(`[Node.js] 파이썬 AI 서버로 분석 위임 요청 전송: ${product_url}`);
        
        // 파이썬 FastAPI 서버 엔드포인트로 데이터 전송 및 로딩(await)
        const pythonResponse = await axios.post('http://localhost:8000/analyze', {
            url: product_url
        });

        // 파이썬이 돌려준 최종 JSON 응답 확인
        if (pythonResponse.data.success) {
            console.log(`[Node.js] 파이썬으로부터 연산 완료 결과 수신 완료.`);
            // Client 에게 파이썬이 준 데이터를 그대로 출력
            res.json({ success: true, data: pythonResponse.data.data });
        } 
        else {
            res.status(500).json({ success: false, error: "파이썬 서버 연산 실패" });
        }
    } 
    catch (error) {
        console.error("[Node.js 내부 통신 에러]", error.message);
        res.status(500).json({ success: false, error: "파이썬 AI 서버가 응답하지 않거나 연결할 수 없습니다." });
    }
});

// 지정되지 않은 모든 경로는 메인 화면으로 유도
app.get('/', (req, res) => {
    res.sendFile(join(__dirname, 'frontend/public', 'main.html'));
});

app.listen(PORT, () => {
    console.log(`[Lumina API Server] 시스템 정상 구동 중`);
    console.log(`접속 주소: http://localhost:${PORT}\n`);
});