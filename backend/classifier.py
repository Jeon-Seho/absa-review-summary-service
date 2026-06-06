# 결과 분리, 대표 문장 선정

from collections import defaultdict
import json

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import torch

# 감정 기준 분류
def classify_by_sentiment(results: list[dict]) -> list[dict]:
    # 감정 분석 결과를 중복없이 집계
    sentiments_set = defaultdict(set)
    
    for result in results:
        sentiments_set[result['sentence']].add(result['sentiment'])

    sentiment_dict = {"pos": [], "neu": [], "neg": []}

    # 3가지 감정 중 하나로 분류
    for sentence, sentiments in sentiments_set.items():
        final_sentiment = ""

        if len(sentiments) == 1:
            final_sentiment = list(sentiments)[0]
        elif 'pos' in sentiments and 'neg' in sentiments: # 긍정 + 부정
            final_sentiment = 'neu'
        elif 'pos' in sentiments and 'neu' in sentiments: # 긍정 + 중립
            final_sentiment = 'pos'
        elif 'neg' in sentiments and 'neu' in sentiments: # 부정 + 중립
            final_sentiment = 'neg'

        sentiment_dict[final_sentiment].append(sentence)

    # print(json.dumps(sentiment_dict, indent=2, ensure_ascii=False))
    
    return sentiment_dict
    
# 속성 별 감정 기준 분류
def classify_by_aspect_based_sentiment(results: list[dict]) -> list[dict]:
    aspect_sentiment_dict = {}

    for result in results:
        # 처음 추가되는 속성인 경우 양식 삽입
        if result['aspect'] not in aspect_sentiment_dict:
            aspect_sentiment_dict[result['aspect']] = {"pos": [], "neu": [], "neg": []}

        aspect_sentiment_dict[result['aspect']][result['sentiment']].append(result['sentence'])

    # print(json.dumps(aspect_sentiment_dict, indent=2, ensure_ascii=False))
    
    return aspect_sentiment_dict

# 문장 클러스터링
def select_representative_by_cluster(texts: str, embeddings, n_clusters: int = 3) -> list[dict]:
    """
    각 감성 그룹 내에서 최대 n_clusters개의 대표 리뷰를 추출합니다.
    리뷰 수가 n_clusters보다 적으면, 리뷰 수만큼만 클러스터를 만듭니다.
    """
    # 방어 코드: 요청한 개수보다 실제 리뷰 수가 적으면 클러스터 수를 리뷰 수에 맞춤
    n_clusters = min(n_clusters, len(texts))

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(embeddings)

    representatives = []
    total_reviews = len(texts)

    for cluster_id in range(n_clusters):
        cluster_indices = np.where(labels == cluster_id)[0]
        cluster_embeddings = embeddings[cluster_indices]

        # 중심점 구하기 및 유사도 계산
        centroid = kmeans.cluster_centers_[cluster_id].reshape(1, -1)
        similarities = cosine_similarity(cluster_embeddings, centroid).reshape(-1)

        best_idx_in_cluster = np.argmax(similarities)
        original_idx = cluster_indices[best_idx_in_cluster]

        # 설명력 지표 계산
        similarity_score = similarities[best_idx_in_cluster]
        representativeness = round(float(similarity_score) * 100, 1)
        coverage = round((len(cluster_indices) / total_reviews) * 100, 1)

        representatives.append({
            "review": texts[original_idx],
            "cluster_id": cluster_id,
            "cluster_size": len(cluster_indices),
            "representativeness": representativeness,
            "coverage": coverage
        })

    # 많은 리뷰가 뭉쳐있는 그룹 순으로 내림차순 정렬
    return sorted(representatives, key=lambda x: x["cluster_size"], reverse=True)

# 대표 문장 추출
def get_sentiment_representatives(review_data: list[dict], model: SentenceTransformer, max_reps: int) -> dict:
    representative_sentence_dict = {}

    for sentiment, texts in review_data.items():
        # 문장이 아예 없거나 빈 리스트인 경우
        if not texts or len(texts) == 0:
            representative_sentence_dict[sentiment] = []
            continue

        # 문장이 있지만 요청한 대표 개수(3개)보다 적은 경우
        # 클러스터링을 돌리지 않고, 있는 문장 전부를 각각 대표성 100%로 간주하여 반환
        if len(texts) < max_reps:
            single_reps = []
            for idx, text in enumerate(texts):
                single_reps.append({
                    "review": text,
                    "cluster_id": idx,
                    "cluster_size": 1,
                    "representativeness": 100.0,
                    "coverage": round((1 / len(texts)) * 100, 1)
                })
            representative_sentence_dict[sentiment] = single_reps
            continue

        # 문장이 3개 이상일 때만 안전하게 임베딩 및 클러스터링 진행
        device = "cuda" if torch.cuda.is_available() else "cpu"
        embeddings = model.encode(texts, device=device)
        try:
            rep_result = select_representative_by_cluster(texts, embeddings, n_clusters=max_reps)
            representative_sentence_dict[sentiment] = rep_result
        except Exception as e:
            representative_sentence_dict[sentiment] = []
            
    # # 결과 리포트 출력
    # print("소비자 감성 분석 및 대표 근거 리포트 (최대 3개 추출)\n" + "="*50)
    # for sentiment in ["pos", "neu", "neg"]:
    #     reps = representative_sentence_dict``.get(sentiment, [])
    #     total_count = len(test_data[sentiment])
    #     print(f"[{sentiment.upper()} 의견 그룹] ({total_count}개 중 {len(reps)}개 추출)")

    #     if not reps:
    #         print("(데이터가 없어 대표 문장을 추출할 수 없습니다.)\n" + "-" * 50)
    #         continue

    #     for i, rep in enumerate(reps):
    #         print(f"   대표 {i+1}: \"{rep['review']}\"")
    #         print(f"     - 대표성 점수 : {rep['representativeness']}% | 의견 지분율 : {rep['coverage']}%")
    #     print("-" * 50)

    #     #대표성 점수 == 클러스터링의 기준이 되는 값과의 코사인 유사도
    #     #의견 지분율 == (현재 클러스터에 모인 리뷰의 수 / 전체 총 리뷰 수) * 100

    return representative_sentence_dict

# 결과 분류
def classify_result(results: list[dict], embed_model: SentenceTransformer) -> tuple[dict, dict, dict]:
    sentiment_dict = classify_by_sentiment(results)                     # 감정 기준 분류
    aspect_sentiment_dict = classify_by_aspect_based_sentiment(results) # 속성별 감정 기준 분류
    representative_sentence_dict = get_sentiment_representatives(sentiment_dict, embed_model, max_reps=3)  # 대표 문장 추출
    
    return sentiment_dict, aspect_sentiment_dict, representative_sentence_dict