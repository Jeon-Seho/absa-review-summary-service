import torch
from torch.utils.data import Dataset
import pandas as pd

# 모델 학습 전용 데이터셋
class ABSADataset(Dataset):
    def __init__(self, df, tokenizer, max_len=128):
        self.df = df
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        
        review = row["SentimentText"]
        aspect = row['Aspect']

        encoding = self.tokenizer(
            aspect,
            review,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "aspect_label": torch.tensor(row["AspectConfidence"], dtype=torch.long),
            "sentiment_label": torch.tensor(row["SentimentPolarity"], dtype=torch.long)
        }
        
class MultiLabelABSADataset(Dataset):
    def __init__(self, df, tokenizer, aspects, max_length=128):
        self.df = df
        self.tokenizer = tokenizer
        self.aspects = list(aspects)
        self.max_length = max_length

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        sample = self.df.iloc[idx]

        encoding = self.tokenizer(
            sample["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )

        item = {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "aspect_labels": torch.tensor(
                sample["aspect_labels"],
                dtype=torch.float
            ),
            "sentiment_labels": torch.tensor(
                sample["sentiment_labels"],
                dtype=torch.long
            )
        }

        # 이건 있는 경우에만 사용
        if "token_type_ids" in encoding:
            item["token_type_ids"] = encoding["token_type_ids"].squeeze(0)

        return item
    
def create_negative_aspect_samples(data, seed):
    negative_data = []

    # 각 aspect의 positive 개수
    aspect_counts = data['Aspect'].value_counts()

    for target_aspect, count in aspect_counts.items():

        # target_aspect가 아닌 문장들만 후보
        candidate_rows = data[
            data['Aspect'] != target_aspect
        ]

        # 중복 허용 여부
        sampled_rows = candidate_rows.sample(
            n=count,
            replace=len(candidate_rows) < count,
            random_state=seed
        )

        for _, row in sampled_rows.iterrows():

            negative_data.append({
                "SentimentText": row["SentimentText"],
                "Aspect": target_aspect,
                "SentimentPolarity": -1,   # mask
                "AspectConfidence": 0
            })

    return negative_data
    
def create_datasetV2(df, aspects, seed, ratio = 0.8):
    samples = []

    aspects = list(aspects)

    # 현재 같은 리뷰여도 측면별로 행이 나눠져있기 때문에 groupby로 묶기
    grouped = df.groupby("SentimentText", sort=False)

    # 감정, 측면 label 배열 만들기
    for text, group in grouped:
        aspect_labels = [0] * len(aspects)
        sentiment_labels = [-1] * len(aspects)

        for _, row in group.iterrows():
            aspect = row["Aspect"]

            if aspect not in aspects:
                continue

            idx = aspects.index(aspect)

            aspect_labels[idx] = int(row["AspectConfidence"])
            sentiment_labels[idx] = int(row["SentimentPolarity"])

        samples.append({
            "text": text,
            "aspect_labels": aspect_labels,
            "sentiment_labels": sentiment_labels
        })
        
    samples = pd.DataFrame(samples)

    train_data = samples.sample(frac=ratio, random_state=seed)
    valid_data = samples.drop(train_data.index)
    train_data = train_data
    
    return train_data, valid_data