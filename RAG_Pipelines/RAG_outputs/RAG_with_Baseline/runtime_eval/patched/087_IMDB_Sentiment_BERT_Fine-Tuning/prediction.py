
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, f1_score
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, AdamW
from datasets import load_dataset

# Set random seeds for reproducibility
np.random.seed(42)
torch.manual_seed(42)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(42)

# Device configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load IMDB dataset from Hugging Face datasets
print("Loading IMDB dataset...")
dataset = load_dataset('imdb')

# Use a subset for faster training (adjust as needed)
train_size = 2000
val_size = 500
train_data = dataset['train'].shuffle(seed=42).select(range(train_size))
val_data = dataset['test'].shuffle(seed=42).select(range(val_size))

# Load pre-trained BERT tokenizer
print("Loading BERT tokenizer...")
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Custom Dataset class
class IMDBDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(label, dtype=torch.long)
        }

# Prepare datasets
train_texts = train_data['text']
train_labels = train_data['label']
val_texts = val_data['text']
val_labels = val_data['label']

train_dataset = IMDBDataset(train_texts, train_labels, tokenizer)
val_dataset = IMDBDataset(val_texts, val_labels, tokenizer)

# Create data loaders
batch_size = 0
train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

# Load pre-trained BERT model for sequence classification
print("Loading BERT model...")
model = BertForSequenceClassification.from_pretrained(
    'bert-base-uncased',
    num_labels=2
)
model.to(device)

# Optimizer with small learning rate
learning_rate = 2e-5
optimizer = AdamW(model.parameters(), lr=learning_rate)

# Training function
def train_epoch(model, data_loader, optimizer, device):
    model.train()
    total_loss = 0
    
    for batch in data_loader:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)
        
        optimizer.zero_grad()
        
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )
        
        loss = outputs.loss
        total_loss += loss.item()
        
        loss.backward()
        optimizer.step()
    
    return total_loss / len(data_loader)

# Evaluation function
def evaluate(model, data_loader, device):
    model.eval()
    predictions = []
    true_labels = []
    
    with torch.no_grad():
        for batch in data_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)
            
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )
            
            logits = outputs.logits
            preds = torch.argmax(logits, dim=1)
            
            predictions.extend(preds.cpu().numpy())
            true_labels.extend(labels.cpu().numpy())
    
    accuracy = accuracy_score(true_labels, predictions)
    f1 = f1_score(true_labels, predictions, average='binary')
    
    return accuracy, f1

# Training loop
num_epochs = 5
train_losses = []
val_accuracies = []
val_f1_scores = []

print("Starting training...")
for epoch in range(num_epochs):
    print(f"\nEpoch {epoch + 1}/{num_epochs}")
    
    # Train
    train_loss = train_epoch(model, train_loader, optimizer, device)
    train_losses.append(train_loss)
    print(f"Training Loss: {train_loss:.4f}")
    
    # Evaluate
    val_accuracy, val_f1 = evaluate(model, val_loader, device)
    val_accuracies.append(val_accuracy)
    val_f1_scores.append(val_f1)
    print(f"Validation Accuracy: {val_accuracy:.4f}")
    print(f"Validation F1 Score: {val_f1:.4f}")

# Plot training loss and validation accuracy
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Plot training loss
ax1.plot(range(1, num_epochs + 1), train_losses, marker='o', color='blue', label='Training Loss')
ax1.set_xlabel('Epoch')
ax1.set_ylabel('Loss')
ax1.set_title('Training Loss Across Epochs')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Plot validation accuracy
ax2.plot(range(1, num_epochs + 1), val_accuracies, marker='s', color='green', label='Validation Accuracy')
ax2.set_xlabel('Epoch')
ax2.set_ylabel('Accuracy')
ax2.set_title('Validation Accuracy Across Epochs')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('bert_training_metrics.png', dpi=100, bbox_inches='tight')
print('[FAST_EVAL] plt.show() skipped')

# Final evaluation summary
print("\n" + "="*50)
print("Final Results:")
print("="*50)
print(f"Final Training Loss: {train_losses[-1]:.4f}")
print(f"Final Validation Accuracy: {val_accuracies[-1]:.4f}")
print(f"Final Validation F1 Score: {val_f1_scores[-1]:.4f}")
print("="*50)

# Example prediction
print("\nExample Prediction:")
sample_text = "This movie was absolutely fantastic! I loved every minute of it."
encoding = tokenizer(
    sample_text,
    add_special_tokens=True,
    max_length=128,
    padding='max_length',
    truncation=True,
    return_tensors='pt'
)

model.eval()
with torch.no_grad():
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)
    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    prediction = torch.argmax(outputs.logits, dim=1).item()

sentiment = "Positive" if prediction == 1 else "Negative"
print(f"Text: {sample_text}")
print(f"Predicted Sentiment: {sentiment}")