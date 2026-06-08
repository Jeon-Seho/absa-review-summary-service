#측면 및 긍/부정 분류 모델 생성
import torch
import torch.nn as nn
from transformers import AutoModel

# V1
class ABSAModel(nn.Module):
    def __init__(self, model_name="monologg/koelectra-base-v3-discriminator"):
        super().__init__()

        self.encoder = AutoModel.from_pretrained(model_name)

        hidden_size = self.encoder.config.hidden_size

        #self.dropout = nn.Dropout(0.1)

        # aspect 존재 여부
        self.aspect_classifier = nn.Linear(hidden_size, 2)
        #self.aspect_classifier = nn.Linear(hidden_size, 1)

        # sentiment 분류
        self.sentiment_classifier = nn.Linear(hidden_size, 3)

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        cls_output = outputs.last_hidden_state[:, 0]

        #cls_output = self.dropout(cls_output)

        aspect_logits = self.aspect_classifier(cls_output)
        sentiment_logits = self.sentiment_classifier(cls_output)

        return aspect_logits, sentiment_logits

# V2
class ABSAModelV2(nn.Module):
    def __init__(self, model_name="monologg/koelectra-base-v3-discriminator"):
        super().__init__()

        self.encoder = AutoModel.from_pretrained(model_name)

        hidden_size = self.encoder.config.hidden_size
        
        self.attention = nn.Linear(hidden_size, 1)

        # aspect 존재 여부
        #self.aspect_classifier = nn.Linear(hidden_size, 2)
        self.aspect_classifier = nn.Linear(hidden_size, 1)

        # sentiment 분류
        self.sentiment_classifier = nn.Linear(hidden_size, 3)

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        hidden = outputs.last_hidden_state
        
        score = self.attention(hidden).squeeze(-1)
        # [B, T]

        score = score.masked_fill(attention_mask == 0, -1e9)

        attn = torch.softmax(score, dim=1).unsqueeze(-1)
        # [B, T, 1]
        
        context = torch.sum(hidden * attn, dim=1)
        # [B, H]

        aspect_logits = self.aspect_classifier(context)
        sentiment_logits = self.sentiment_classifier(context)

        return aspect_logits, sentiment_logits

# V3    
class ABSAModelV3(nn.Module):
    def __init__(self, num_aspect, model_name="monologg/koelectra-base-v3-discriminator"):
        super().__init__()

        self.encoder = AutoModel.from_pretrained(model_name)

        hidden_size = self.encoder.config.hidden_size

        # aspect 존재 여부
        self.aspect_classifier = nn.Linear(hidden_size, num_aspect)

        # sentiment 분류
        self.sentiment_classifier = nn.Linear(hidden_size, num_aspect * 3)
        
        self.num_aspect = num_aspect

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )

        cls_output = outputs.last_hidden_state[:, 0, :]


        aspect_logits = self.aspect_classifier(cls_output)

        sentiment_logits = self.sentiment_classifier(cls_output)
        sentiment_logits = sentiment_logits.view(
            -1,
            self.num_aspect,
            3
        )

        return aspect_logits, sentiment_logits