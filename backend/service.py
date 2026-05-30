# 오케스트레이터

from crawler import fetch_reviews
from inference import infer
from classifier import classify_result
from analyzer import analyze
from aggregator import build_final_result

import asyncio

async def run(url: str, device, infer_model, tokenizer, embed_model, gemini_client) -> dict:
    print("---------- 크롤링 시작 ----------")
    yield {"step": "크롤링 중", "data": None}
    await asyncio.sleep(0)
    output = await fetch_reviews(url)   # 리뷰 노이즈 제거, 크롤링 및 문장 분리
    print("---------- 크롤링 종료 ----------\n")
    
    print("---------- 추론 시작 ----------")
    yield {"step": "추론 중", "data": None}
    await asyncio.sleep(0)
    absa_result = infer(output["sentences"], device, infer_model, tokenizer)    # 모델 추론
    print("---------- 추론 종료 ----------\n")
    
    print("---------- 분류 시작 ----------")
    yield {"step": "분류 중", "data": None}
    await asyncio.sleep(0)
    sentiment_dict, aspect_sentiment_dict, representative_sentence_dict = classify_result(absa_result, embed_model) # 추론 결과 분류
    print("---------- 분류 종료----------\n")
    
    print("---------- 분석 시작 ----------")
    yield {"step": "분석 중", "data": None}
    await asyncio.sleep(0)
    statistics_result, summary = await analyze(aspect_sentiment_dict, sentiment_dict, gemini_client)    # 분석 통계, 요약
    print("---------- 분석 종료 ----------\n")
    
    result = build_final_result(
        output,
        statistics_result,
        representative_sentence_dict,
        summary
    )
    yield {"step": "완료", "data": result}