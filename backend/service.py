# 오케스트레이터

from crawler import fetch_reviews
from inference import infer
from classifier import classify_result
from analyzer import analyze
from aggregator import build_final_result

import asyncio
import logging
import time

logger = logging.getLogger("logger")

async def run(url: str, device, infer_model, tokenizer, embed_model, gemini_client):
    total_t = time.perf_counter()
    
    # 리뷰 수집 및 문장 분리
    logger.info("크롤링을 시작합니다.")
    yield {"step": "크롤링 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    output = await fetch_reviews(url)
    logger.info(f"크롤링을 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    # 모델 추론
    logger.info("추론을 시작합니다.")
    yield {"step": "추론 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    absa_result = infer(output["sentences"], device, infer_model, tokenizer)
    logger.info(f"추론을 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    # 추론 결과 분류
    logger.info("분류를 시작합니다.")
    yield {"step": "분류 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    sentiment_dict, aspect_sentiment_dict, representative_sentence_dict = classify_result(absa_result, embed_model)
    logger.info(f"분류를 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    # 통계 계산, 요약 생성
    logger.info("분석을 시작합니다.")
    yield {"step": "분석 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    statistics_result, summary = await analyze(aspect_sentiment_dict, sentiment_dict, gemini_client)
    logger.info(f"분석을 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    # 결과 조립
    result = build_final_result(
        output,
        statistics_result,
        representative_sentence_dict,
        summary
    )
    
    logger.info(f"전체 소요 시간: {time.perf_counter() - total_t:.2f}s")
    yield {"step": "완료", "data": result}