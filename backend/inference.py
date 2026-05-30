# 모델 생성, 호출 및 추론

import sys, os
from pathlib import Path
import json
from typing import Literal

import numpy as np
import torch
from transformers import AutoTokenizer

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from model.model.make_model import ABSAModelV3

ASPECT_LIST = ['가격', '음량/음질', '화질', '사이즈', '소음', '편의성', '디자인', '무게', '기능', '시간/속도', '조작성', '품질', '용량', '제품구성', '제조일/제조사',
'색상', '내구성', '배터리', '소재']

# 모델 생성
def init_model() -> tuple:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ABSAModelV3(num_aspect=len(ASPECT_LIST)).to(device)
    
    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # os.path.join(BASE_DIR, "model", "final_review_classifier_modelV3(KoElectra).pt")
    
    model_path = ROOT_DIR / "model" / "models" / "final_review_classifier_modelV3(KoElectra).pt"

    checkpoint = torch.load(
        model_path,
        map_location=device
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        "monologg/koelectra-base-v3-discriminator"
    )
    
    return device, model, tokenizer

# 모델 추론
def infer(sentences: list[str], device: Literal["cuda", "cpu"], model: ABSAModelV3, tokenizer: AutoTokenizer) -> list[dict]:
    model.eval()    # 추론 모드로 전환
    
    THRESHOLD = 0.8 # 임계값
    USE_FALLBACK_TOP1 = False  # True면 아무 것도 없을 때 최고점 1개 강제 선택

    results = []

    with torch.no_grad():
        for idx, sentence in enumerate(sentences):
            encoding = tokenizer(
                sentence,
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=128
            )
            encoding = {k: v.to(device) for k, v in encoding.items()}

            aspect_logits, sentiment_logits = model(**encoding)

            aspect_probs = torch.sigmoid(aspect_logits)[0].cpu().numpy()
            sentiment_ids = torch.argmax(sentiment_logits, dim=-1)[0].cpu().numpy()

            selected_idx = np.where(aspect_probs >= THRESHOLD)[0]

            if len(selected_idx) == 0 and USE_FALLBACK_TOP1:
                selected_idx = np.array([int(np.argmax(aspect_probs))])

            for i in selected_idx:
                results.append({
                    "sentence": sentences[idx],
                    "aspect": ASPECT_LIST[i],
                    "aspect_prob": float(aspect_probs[i]),
                    "sentiment": {0: "neg", 1: "neu", 2: "pos"}[int(sentiment_ids[i])]
                })
    
    return results