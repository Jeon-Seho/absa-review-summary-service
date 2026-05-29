# 요약 및 통계 수행

from google import genai
from google.genai import types
import json

# 베이지안 평균
def bayesian_score(positive_ratio: float, n: int, global_mean: float, C: float) -> float:
    return (positive_ratio * n + global_mean * C) / (n + C)

# 통계 계산
def calc_statistics(aspect_sentiment_dict: dict) -> dict:
    aspect_statistics = {}
    total_statistics = [0, 0, 0]

    for key, value in aspect_sentiment_dict.items():
        pos_len = len(value["pos"])
        neu_len = len(value["neu"])
        neg_len = len(value["neg"])
        total_len = pos_len + neu_len + neg_len

        aspect_statistics[key] = {
            "total_len": total_len,
            "pos_len": pos_len,
            "neu_len": neu_len,
            "neg_len": neg_len
        }

        total_statistics[0] += pos_len
        total_statistics[1] += neu_len
        total_statistics[2] += neg_len

    total_len = sum(total_statistics)
    
    # 내림차순 정렬
    aspect_statistics = dict(sorted(aspect_statistics.items(), key=lambda item:item[1]["total_len"], reverse=True))
    
    # 전체 통계
    # print(
    #     f"전체 {total_len}건, "
    #     f"긍정 {total_statistics[0]}건({total_statistics[0] / total_len:.2%}), "
    #     f"중립 {total_statistics[1]}건({total_statistics[1] / total_len:.2%}), "
    #     f"부정 {total_statistics[2]}건({total_statistics[2] / total_len:.2%})"
    # )
    # print()

    # 속성별 통계
    # for key, value in aspect_statistics.items():
    #     print(
    #         f"{key:<6}\t"
    #         f"전체: {value["total_len"]:>3}건, "
    #         f"긍정: {value["pos_len"]:>3}건({value["pos_len"] / value["total_len"]:>7.2%}), "
    #         f"중립: {value["neu_len"]:>3}건({value["neu_len"] / value["total_len"]:>7.2%}), "
    #         f"부정: {value["neg_len"]:>3}건({value["neg_len"] / value["total_len"]:>7.2%})"
    #     )

    # print(json.dumps(aspect_statistics, indent=2, ensure_ascii=False))
    
    return calc_score(aspect_statistics, total_statistics)

# 점수 계산
def calc_score(aspect_statistics: dict, total_statistics: list[int]) -> dict:
    score_list = {}
    final_score = 0
    total_len = sum(total_statistics)

    for key, value in aspect_statistics.items():
        score = round(bayesian_score(
            value['pos_len'] / value['total_len'],  # 해당 속성의 긍정 비율
            value["total_len"],                     # n: 해당 속성의 리뷰 수
            total_statistics[0] / total_len,        # 전체 긍정 비율
            total_len / len(aspect_statistics.keys())      # C: 속성별 평균 리뷰 수(신뢰 임계값)
        ) * 100, 2)
        score_list[key] = score

        weight = value["total_len"] / total_len     # 리뷰 수 비례 가중치
        final_score += score * weight
    
    # print(score_list)

    # 상, 하위 2개 속성 선택
    top_score = dict(sorted(score_list.items(), key=lambda item: item[1], reverse=True)[:2])
    bottom_score = dict(sorted(score_list.items(), key=lambda item: item[1])[:2])
    
    # print(f"Final Score: {final_score}")
    # print(top_score, bottom_score)

    return {"total_score": round(final_score, 2),
            "top_aspect_score": top_score,
            "bottom_aspect_score": bottom_score
            }

# 요약 생성
async def generate_summary(sentiment_dict: dict, gemini_client: genai.Client) -> str:    
    SYSTEM_PROMPT = """
        당신은 온라인 쇼핑몰의 리뷰 요약 전문가입니다.
        제공되는 리뷰 데이터(긍정:pos, 중립:neu, 부정:neg 분류)를 바탕으로 객관적인 요약본을 작성하세요.

        [작성 규칙]
        1. 분량 제한: 반드시 공백 포함 '150자 ~ 250자' 사이로 작성하세요. (글자 수를 엄격히 준수할 것)
        2. 균형감: 특정 감정에 치우치지 않고, 긍정과 부정의 핵심 의견을 균등하게 반영하세요.
        3. 내용 강조: 제품의 어떤 속성(예: 배터리, 디자인, 가격 등)이 긍정적이고 부정적인지 명확히 대조하여 작성하세요.
        4. 말투: 문장은 "~합니다", "~점은 아쉽습니다"와 같이 정중하고 객관적인 어조로 통일하세요.
        5. 제한 조건: 제품이 개선되어야 할 점을 언급하지 마세요. 반드시 주어진 데이터를 요약 및 정리하는 역할만 수행하세요.
        6. 예외 처리: 제공된 리뷰 데이터가 비어있다면 반드시 "리뷰 데이터가 존재하지 않습니다."라는 문장을 반환하세요.
    """
    
    user_contents = f"분석할 리뷰 데이터(JSON):\n```json\n{json.dumps(sentiment_dict, ensure_ascii=False, indent=2)}\n```"
    
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.1,
        max_output_tokens=500
    )
    
    stream = gemini_client.models.generate_content_stream(
        model="gemini-3.1-flash-lite",
        contents=user_contents,
        config=config
    )

    result = ""
    for chunk in stream:
        if chunk.text:
            result += chunk.text

    return result.strip()

async def analyze(aspect_sentiment_dict: dict, sentiment_dict: dict, gemini_client: genai.Client) -> tuple[dict, str]:
    statistics_result = calc_statistics(aspect_sentiment_dict) # 통계
    summary_result = await generate_summary(sentiment_dict, gemini_client)  # 요약
    
    return statistics_result, summary_result