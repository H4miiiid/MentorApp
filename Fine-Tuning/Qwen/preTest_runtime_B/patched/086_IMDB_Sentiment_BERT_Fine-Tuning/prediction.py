
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Load pre-trained model and tokenizer
model_name = 'bert-base-uncased'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2)

# Tokenize and encode the input text
input_text = "This movie is great!"
inputs = tokenizer(input_text, return_tensors='pt')

# Perform inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits

# Get the predicted label
predicted_label = torch.argmax(logits, dim=1).item()
print(predicted_label)