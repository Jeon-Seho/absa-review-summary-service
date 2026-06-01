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
    
    logger.info("크롤링을 시작합니다.")
    yield {"step": "크롤링 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    output = await fetch_reviews(url)   # 리뷰 노이즈 제거, 크롤링 및 문장 분리
    logger.info(f"크롤링을 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    logger.info("추론을 시작합니다.")
    yield {"step": "추론 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    absa_result = infer(output["sentences"], device, infer_model, tokenizer)    # 모델 추론
    logger.info(f"추론을 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    logger.info("분류를 시작합니다.")
    yield {"step": "분류 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    sentiment_dict, aspect_sentiment_dict, representative_sentence_dict = classify_result(absa_result, embed_model) # 추론 결과 분류
    logger.info(f"분류를 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    logger.info("분석을 시작합니다.")
    yield {"step": "분석 중", "data": None}
    await asyncio.sleep(0)
    t = time.perf_counter()
    statistics_result, summary = await analyze(aspect_sentiment_dict, sentiment_dict, gemini_client)    # 분석 통계, 요약
    logger.info(f"분석을 종료합니다. ({time.perf_counter() - t:.2f}s)")
    
    result = build_final_result(
        output,
        statistics_result,
        representative_sentence_dict,
        summary
    )
    
    logger.info(f"전체 소요 시간: {time.perf_counter() - total_t:.2f}s")
    yield {"step": "완료", "data": result}