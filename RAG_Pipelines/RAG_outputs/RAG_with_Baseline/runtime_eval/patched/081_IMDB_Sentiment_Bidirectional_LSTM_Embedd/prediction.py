
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from tensorflow.keras.datasets import imdb
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Bidirectional, LSTM, Dense, Dropout
from sklearn.metrics import roc_auc_score
import matplotlib.pyplot as plt

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# Configuration
max_features = 10000  # Number of words to consider as features
maxlen = 200  # Cut texts after this number of words
embedding_dim = 128
lstm_units = 64
batch_size = 32
epochs = 5

# Load the IMDB dataset
print("Loading IMDB dataset...")
(x_train, y_train), (x_test, y_test) = imdb.load_data(num_words=max_features)

print(f"Training samples: {len(x_train)}")
print(f"Test samples: {len(x_test)}")

# Pad sequences to ensure uniform length
print("Padding sequences...")
x_train = pad_sequences(x_train, maxlen=maxlen)
x_test = pad_sequences(x_test, maxlen=maxlen)

print(f"x_train shape: {x_train.shape}")
print(f"x_test shape: {x_test.shape}")

# Build the bidirectional LSTM model with embedding layer
print("Building model...")
model = Sequential()

# Embedding layer: converts word indices to dense vectors
model.add(Embedding(input_dim=max_features, output_dim=embedding_dim, input_length=maxlen))

# Bidirectional LSTM layer with dropout regularization
model.add(Bidirectional(LSTM(lstm_units, return_sequences=False)))

# Dropout for regularization
model.add(Dropout(0.5))

# Output layer for binary classification
model.add(Dense(1, activation='sigmoid'))

# Compile the model
model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy']
)

print("Model summary:")
model.summary()

# Train the model
print("\nTraining model...")
history = model.fit(
    x_train, y_train,
    batch_size=batch_size,
    epochs=epochs,
    validation_split=0.2,
    verbose=1
)

# Evaluate the model on the test set
print("\nEvaluating model on test set...")
test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)
print(f"Test Loss: {test_loss:.4f}")
print(f"Test Accuracy: {test_accuracy:.4f}")

# Predict probabilities for ROC-AUC calculation
y_pred_proba = model.predict(x_test, verbose=0).flatten()

# Calculate ROC-AUC score
roc_auc = roc_auc_score(y_test, y_pred_proba)
print(f"Test ROC-AUC: {roc_auc:.4f}")

# Plot training history
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot accuracy
axes[0].plot(history.history['accuracy'], label='Train Accuracy')
axes[0].plot(history.history['val_accuracy'], label='Validation Accuracy')
axes[0].set_title('Model Accuracy')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Accuracy')
axes[0].legend()
axes[0].grid(True)

# Plot loss
axes[1].plot(history.history['loss'], label='Train Loss')
axes[1].plot(history.history['val_loss'], label='Validation Loss')
axes[1].set_title('Model Loss')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('Loss')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig('training_history.png', dpi=100, bbox_inches='tight')
print("\nTraining history plot saved as 'training_history.png'")
print('[FAST_EVAL] plt.show() skipped')

# Example prediction on a few test samples
print("\nExample predictions:")
num_examples = 5
for i in range(num_examples):
    prediction = y_pred_proba[i]
    actual = y_test[i]
    sentiment = "Positive" if prediction > 0.5 else "Negative"
    actual_sentiment = "Positive" if actual == 1 else "Negative"
    print(f"Sample {i+1}: Predicted={sentiment} (prob={prediction:.4f}), Actual={actual_sentiment}")

print("\nModel training and evaluation complete!")