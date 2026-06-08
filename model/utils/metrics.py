from sklearn.metrics import classification_report, f1_score
from tqdm.auto import tqdm
import numpy as np
import pandas as pd
import torch

# def evaluation_dataset(device, model, tokenizer, dataset, aspects, threshold=None):
#     all_aspect_preds = []
#     all_aspect_labels = []

#     all_sentiment_preds = []
#     all_sentiment_labels = []

#     grouped = dataset.groupby("SentimentText", sort=False)

#     progress_bar = tqdm(grouped, total=grouped.ngroups)

#     with torch.no_grad():
#         for review, group in progress_bar:
#             aspect_label_map = {aspect: 0 for aspect in aspects}
#             sentiment_label_map = {aspect: -1 for aspect in aspects}

#             for _, row in group.iterrows():
#                 aspect = row["Aspect"]
#                 aspect_conf = int(row["AspectConfidence"])
#                 sentiment = int(row["SentimentPolarity"])

#                 if aspect in aspect_label_map:
#                     aspect_label_map[aspect] = aspect_conf
#                     sentiment_label_map[aspect] = sentiment

#             aspect_labels = np.array([aspect_label_map[aspect] for aspect in aspects])
#             sentiment_labels = np.array([sentiment_label_map[aspect] for aspect in aspects])

#             texts = [review] * len(aspects)
#             aspect_texts = list(aspects)

#             encoding = tokenizer(
#                 texts,
#                 aspect_texts,
#                 return_tensors="pt",
#                 truncation=True,
#                 padding=True,
#                 max_length=128
#             )

#             input_ids = encoding["input_ids"].to(device)
#             attention_mask = encoding["attention_mask"].to(device)

#             aspect_logits, sentiment_logits = model(
#                 input_ids=input_ids,
#                 attention_mask=attention_mask
#             )

#             # if threshold is None:
#             #     aspect_preds = torch.argmax(aspect_logits, dim=-1).cpu().numpy()
#             # else:
#             #     aspect_probs = torch.softmax(aspect_logits, dim=-1)[:, 1]
#             #     aspect_preds = (aspect_probs >= threshold).long().cpu().numpy()
            
#             aspect_logits = aspect_logits.squeeze(-1)                 # [num_aspects]
#             aspect_probs = torch.sigmoid(aspect_logits)               # [num_aspects]

#             th = 0.5 if threshold is None else threshold
#             aspect_preds = (aspect_probs >= th).long().cpu().numpy() 

#             sentiment_preds = torch.argmax(sentiment_logits, dim=-1).cpu().numpy()

#             all_aspect_preds.extend(aspect_preds.tolist())
#             all_aspect_labels.extend(aspect_labels.tolist())

#             sentiment_mask = sentiment_labels != -1
#             all_sentiment_preds.extend(sentiment_preds[sentiment_mask].tolist())
#             all_sentiment_labels.extend(sentiment_labels[sentiment_mask].tolist())

#     return all_aspect_preds, all_aspect_labels, all_sentiment_preds, all_sentiment_labels

def evaluation_dataset(model, tokenizer, dataset: pd.DataFrame, aspects, device): 
    all_aspect_preds = []
    all_aspect_labels = []

    all_sentiment_preds = []
    all_sentiment_labels = []

    progress_bar = tqdm(
        dataset.itertuples(),
        total=len(dataset)
    )

    with torch.no_grad():
        for idx, row in enumerate(progress_bar):
            # if idx >= 10000:
            #   break;

            aspect_pred = []
            sentiment_pred = []

            # 모든 속성어에 대한 조합을 생성
            texts = [row.SentimentText] * len(aspects)
            aspect_texts = list(aspects)

            # 한번에 encoding 처리
            encoding = tokenizer(
                aspect_texts,
                texts,
                return_tensors="pt",
                truncation=True,
                padding=True
            )

            input_ids = encoding["input_ids"].to(device)
            attention_mask = encoding["attention_mask"].to(device)

            aspect_logits, sentiment_logits = model(
                input_ids,
                attention_mask
            )

            sentiment_pred = torch.argmax(
                sentiment_logits,
                dim=-1
            ).cpu().numpy()

            # 각 Aspect에 대한 logits이 가장 높은 Aspect를 선택
            aspect_pred_idx = int(np.argmax(aspect_logits[:, 1].cpu().numpy()))
            
            # 속성어 index와 긍/부정 저장
            all_aspect_preds.append(aspect_pred_idx)
            all_aspect_labels.append(row.Aspect)

            all_sentiment_preds.append(sentiment_pred[aspect_pred_idx])
            all_sentiment_labels.append(row.SentimentPolarity)
            
    return all_aspect_preds, all_aspect_labels, all_sentiment_preds, all_sentiment_labels

def print_evaluation_report(all_aspect_preds, all_aspect_labels, all_sentiment_preds, all_sentiment_labels, aspects):
    
    print(classification_report(
        all_sentiment_labels,
        all_sentiment_preds,
        target_names=[
            "negative",
            "neutral",
            "positive"
        ]
    ))

    print(classification_report(
        all_aspect_labels,
        all_aspect_preds,
        target_names=aspects
    ))

# def print_evaluation_report(all_aspect_preds, all_aspect_labels, all_sentiment_preds, all_sentiment_labels, aspects):
#     print(classification_report(
#         all_sentiment_labels,
#         all_sentiment_preds,
#         target_names=["negative", "neutral", "positive"]
#     ))
    
#     num_aspects = len(aspects)
#     y_true = np.array(all_aspect_labels).reshape(-1, num_aspects)
#     y_pred = np.array(all_aspect_preds).reshape(-1, num_aspects)

#     print(classification_report(
#         y_true,
#         y_pred,
#         target_names=aspects,
#         zero_division=0
#     ))

def evaluate_val_multilabel(model, val_loader, device, threshold=0.5):
    model.eval()

    aspect_elem_correct = 0
    aspect_elem_total = 0

    aspect_subset_correct = 0
    aspect_subset_total = 0

    sentiment_correct = 0
    sentiment_total = 0

    all_aspect_true = []
    all_aspect_pred = []

    all_sent_true = []
    all_sent_pred = []

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            aspect_labels = batch["aspect_labels"].to(device)          # [B, A], float
            sentiment_labels = batch["sentiment_labels"].to(device)    # [B, A], long, absent=-1

            model_inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }
            if "token_type_ids" in batch:
                model_inputs["token_type_ids"] = batch["token_type_ids"].to(device)

            aspect_logits, sentiment_logits = model(**model_inputs)    # [B, A], [B, A, 3]

            # aspect pred
            aspect_probs = torch.sigmoid(aspect_logits)
            aspect_preds = (aspect_probs >= threshold).float()

            # aspect accuracy
            aspect_elem_correct += (aspect_preds == aspect_labels).sum().item()
            aspect_elem_total += aspect_labels.numel()

            subset_match = (aspect_preds == aspect_labels).all(dim=1)
            aspect_subset_correct += subset_match.sum().item()
            aspect_subset_total += aspect_labels.size(0)

            # sentiment pred (존재 aspect만)
            sentiment_preds = torch.argmax(sentiment_logits, dim=-1)   # [B, A]
            sentiment_mask = sentiment_labels != -1

            if sentiment_mask.any():
                sentiment_correct += (
                    sentiment_preds[sentiment_mask] == sentiment_labels[sentiment_mask]
                ).sum().item()
                sentiment_total += sentiment_mask.sum().item()

                all_sent_true.extend(sentiment_labels[sentiment_mask].cpu().numpy().tolist())
                all_sent_pred.extend(sentiment_preds[sentiment_mask].cpu().numpy().tolist())

            # F1용 수집
            all_aspect_true.append(aspect_labels.cpu().numpy())
            all_aspect_pred.append(aspect_preds.cpu().numpy())

    y_true = np.concatenate(all_aspect_true, axis=0)   # [N, A]
    y_pred = np.concatenate(all_aspect_pred, axis=0)   # [N, A]

    aspect_micro_f1 = f1_score(y_true, y_pred, average="micro", zero_division=0)
    aspect_macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    sentiment_macro_f1 = (
        f1_score(all_sent_true, all_sent_pred, average="macro", zero_division=0)
        if len(all_sent_true) > 0 else 0.0
    )

    return {
        "aspect_elem_acc": aspect_elem_correct / max(aspect_elem_total, 1),
        "aspect_subset_acc": aspect_subset_correct / max(aspect_subset_total, 1),
        "aspect_micro_f1": aspect_micro_f1,
        "aspect_macro_f1": aspect_macro_f1,
        "sentiment_acc": sentiment_correct / max(sentiment_total, 1),
        "sentiment_macro_f1": sentiment_macro_f1,
    }

def classification_report_multilabel_absa(model, data_loader, device, aspects, threshold=0.5):
    model.eval()

    all_aspect_true = []
    all_aspect_pred = []

    all_sent_true = []
    all_sent_pred = []

    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            aspect_labels = batch["aspect_labels"].to(device)          # [B, A]
            sentiment_labels = batch["sentiment_labels"].to(device)    # [B, A], absent=-1

            model_inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }
            if "token_type_ids" in batch:
                model_inputs["token_type_ids"] = batch["token_type_ids"].to(device)

            aspect_logits, sentiment_logits = model(**model_inputs)    # [B, A], [B, A, 3]

            # Aspect 예측 (multi-label)
            aspect_probs = torch.sigmoid(aspect_logits)
            aspect_preds = (aspect_probs >= threshold).float()

            all_aspect_true.append(aspect_labels.cpu().numpy())
            all_aspect_pred.append(aspect_preds.cpu().numpy())

            # Sentiment 예측 (존재 aspect만)
            sentiment_preds = torch.argmax(sentiment_logits, dim=-1)   # [B, A]
            sentiment_mask = sentiment_labels != -1

            if sentiment_mask.any():
                all_sent_true.extend(sentiment_labels[sentiment_mask].cpu().numpy().tolist())
                all_sent_pred.extend(sentiment_preds[sentiment_mask].cpu().numpy().tolist())

    y_true = np.concatenate(all_aspect_true, axis=0)  # [N, A]
    y_pred = np.concatenate(all_aspect_pred, axis=0)  # [N, A]

    print("=== Aspect Classification Report (Multi-label) ===")
    print(classification_report(
        y_true, y_pred,
        target_names=list(aspects),
        zero_division=0
    ))

    print("=== Sentiment Classification Report ===")
    print(classification_report(
        all_sent_true, all_sent_pred,
        target_names=["negative", "neutral", "positive"],
        zero_division=0
    ))

