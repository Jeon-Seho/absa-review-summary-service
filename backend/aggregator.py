# 프론트엔드에 전송할 json 메시지 조립

import json

def build_final_result(reviews: dict, statistics_result: dict, representative_sentence_dict: dict, summary: str) -> dict:
    final_result = {}
    
    # crawler의 xxx로부터 average_rate
    final_result["average_rate"] = reviews["average_review_rate"]
    
    # classifier의 representative_sentence_dict으로부터 감정 별 대표 문장 3개씩
    for sentiment, representative_reviews in representative_sentence_dict.items():
        if sentiment not in final_result:
            final_result[sentiment] = []
            
        for representative_review in representative_reviews:
            final_result[sentiment].append(representative_review["review"])
    
    # analyzer의 statistics_result로부터 total_score, top_aspect_score, bottom_aspect_score
    final_result["total_score"] = statistics_result["total_score"]
    final_result["top_aspect_score"] = statistics_result["top_aspect_score"]
    final_result["bottom_aspect_score"] = statistics_result["bottom_aspect_score"]
    
    # analyzer의 summary로부터 final_summary
    final_result["final_summary"] = summary
    
    # print(json.dumps(final_result, indent=2, ensure_ascii=False))
    
    return final_result