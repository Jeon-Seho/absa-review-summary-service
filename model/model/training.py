from tqdm.auto import tqdm
from torch.utils.data import DataLoader
import torch

def training_model(model, optimizer, loader: DataLoader, 
                   criterion_aspect, criterion_sentiment, device):
    total_loss = 0

    aspect_correct = 0
    aspect_total = 0

    sentiment_correct = 0
    sentiment_total = 0

    # 학습 진행 상황
    progress_bar = tqdm(
        loader,
    )
    
    for batch in progress_bar:

        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)

        aspect_labels = batch["aspect_label"].to(device)
        sentiment_labels = batch["sentiment_label"].to(device)

        optimizer.zero_grad()

        aspect_logits, sentiment_logits = model(
            input_ids,
            attention_mask
        )

        # 측면 Loss
        aspect_loss = criterion_aspect(
            aspect_logits,
            aspect_labels
        )


        # 측면이 부정인 경우는 긍/부정 Loss에서 제외
        mask = (sentiment_labels != -1)

        # 측면이 긍정인 경우에만 Loss 확인
        if mask.any():

            sentiment_loss = criterion_sentiment(
                sentiment_logits[mask],
                sentiment_labels[mask]
            )

        else:
            sentiment_loss = aspect_loss * 0

        loss = (0.7 * aspect_loss) + (1.3 * sentiment_loss)

        # 역전파
        loss.backward()

        # adam 업데이트
        optimizer.step()

        total_loss += loss.item()

        # accuracy 계산(속성어)
        aspect_preds = torch.argmax(
            aspect_logits,
            dim=1
        )

        aspect_correct += (
            aspect_preds == aspect_labels
        ).sum().item()

        aspect_total += aspect_labels.size(0)
        aspect_acc = aspect_correct / aspect_total

        # accuracy 계산(감정)
        if mask.any():
            sentiment_preds = torch.argmax(
                sentiment_logits[mask],
                dim=1
            )

            sentiment_correct += (
                sentiment_preds == sentiment_labels[mask]
            ).sum().item()

            sentiment_total += mask.sum().item()

        sentiment_acc = (
            sentiment_correct / sentiment_total
            if sentiment_total > 0 else 0
        )

        # tqdm에 현재 loss 표시
        progress_bar.set_postfix({
            "loss": f"{loss.item():.4f}",
            "aspect": f"{aspect_loss.item():.4f}",
            "sentiment": f"{sentiment_loss.item():.4f}",
            "a_acc": f"{aspect_acc:.4f}",
            "s_acc": f"{sentiment_acc:.4f}"
        })

    avg_loss = total_loss / len(loader.dataset)
    
    return avg_loss, aspect_acc, sentiment_acc

def training_multi_label_model(model, optimizer, loader: DataLoader, device):
    model.train()
    
    # Loss 함수 생성
    criterion_aspect = torch.nn.BCEWithLogitsLoss()
    criterion_sentiment = torch.nn.CrossEntropyLoss()

    total_loss = 0

    # epoch 시작 시 초기화
    aspect_elem_correct = 0
    aspect_elem_total = 0

    aspect_subset_correct = 0
    aspect_subset_total = 0

    sentiment_correct = 0
    sentiment_total = 0
    
    # 학습 진행 상황
    progress_bar = tqdm(
        loader,
    )

    for batch in progress_bar:

        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)

        aspect_labels = batch["aspect_labels"].to(device)
        sentiment_labels = batch["sentiment_labels"].to(device)
        
        # forward
        model_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }
        if "token_type_ids" in batch:
            model_inputs["token_type_ids"] = batch["token_type_ids"].to(device)

        optimizer.zero_grad()

        aspect_logits, sentiment_logits = model(**model_inputs)
        
        aspect_loss = criterion_aspect(
            aspect_logits,
            aspect_labels
        )

        sentiment_mask = sentiment_labels != -1

        if sentiment_mask.any():
            sentiment_loss = criterion_sentiment(
                sentiment_logits[sentiment_mask],
                sentiment_labels[sentiment_mask]
            )
        else:
            sentiment_loss = torch.tensor(0.0, device=device)

        loss = 0.7 * aspect_loss + 1.3 * sentiment_loss

        # 역전파
        loss.backward()

        # adam 업데이트
        optimizer.step()

        total_loss += loss.item()

        aspect_logits = aspect_logits.squeeze(-1)

        # ===== accuracy (멀티라벨) =====
        # 1) aspect element-wise accuracy
        aspect_probs = torch.sigmoid(aspect_logits)               # [B, A]
        aspect_preds = (aspect_probs >= 0.5).float()              # [B, A]

        aspect_elem_correct += (aspect_preds == aspect_labels).sum().item()
        aspect_elem_total += aspect_labels.numel()
        aspect_elem_acc = aspect_elem_correct / aspect_elem_total

        # 2) aspect subset accuracy (리뷰 단위 완전일치)
        subset_match = (aspect_preds == aspect_labels).all(dim=1) # [B]
        aspect_subset_correct += subset_match.sum().item()
        aspect_subset_total += aspect_labels.size(0)
        aspect_subset_acc = aspect_subset_correct / max(aspect_subset_total, 1)

        # 3) sentiment accuracy (존재 aspect만)
        sentiment_preds = torch.argmax(sentiment_logits, dim=-1)  # [B, A]
        if sentiment_mask.any():
            sentiment_correct += (
                sentiment_preds[sentiment_mask] == sentiment_labels[sentiment_mask]
            ).sum().item()
            sentiment_total += sentiment_mask.sum().item()

        sentiment_acc = sentiment_correct / sentiment_total if sentiment_total > 0 else 0.0

        # tqdm에 현재 loss 표시
        progress_bar.set_postfix({
            "loss": f"{loss.item():.4f}",
            "aspect": f"{aspect_loss.item():.4f}",
            "sentiment": f"{sentiment_loss.item():.4f}",
            "a_acc": f"{aspect_elem_acc:.4f}",
            "a_match_acc": f"{aspect_subset_acc:4f}",
            "s_acc": f"{sentiment_acc:.4f}"
        })
        
    avg_loss = total_loss / len(loader.dataset)
        
    return avg_loss, aspect_elem_acc, aspect_subset_acc, sentiment_acc