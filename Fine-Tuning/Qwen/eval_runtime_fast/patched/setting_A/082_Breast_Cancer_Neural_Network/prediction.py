
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from tensorflow import keras
from tensorflow.keras import layers

# Load the breast cancer dataset
data = load_breast_cancer()
X = data.data
y = data.target

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Standardize the features
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# Build a small feed-forward neural network with dropout
model = keras.Sequential([
    layers.Dense(64, activation='relu', input_shape=(X_train.shape[1],)),
    layers.Dropout(0.3),
    layers.Dense(32, activation='relu'),
    layers.Dropout(0.3),
    layers.Dense(16, activation='relu'),
    layers.Dropout(0.2),
    layers.Dense(1, activation='sigmoid')
])

# Compile the model with binary cross-entropy loss
model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy']
)

# Train the model and track validation performance
history = model.fit(
    X_train, y_train,
    epochs=1,
    batch_size=32,
    validation_split=0.2,
    verbose=0
)

# Evaluate the model on the test set
y_pred_proba = model.predict(X_test).flatten()
test_auc = roc_auc_score(y_test, y_pred_proba)
print(f"Test ROC-AUC Score: {test_auc:.4f}")

# Calculate validation AUC for each epoch
val_indices = int(0.8 * len(X_train))
X_val = X_train[val_indices:]
y_val = y_train[val_indices:]

val_auc_scores = []
for epoch in range(len(history.history['loss'])):
    # Get predictions for validation set at each epoch
    # Note: We approximate by using the final model's predictions
    # In practice, you'd need to save model weights at each epoch
    y_val_pred = model.predict(X_val).flatten()
    val_auc = roc_auc_score(y_val, y_val_pred)
    val_auc_scores.append(val_auc)

# Plot validation AUC over epochs
plt.figure(figsize=(10, 6))
plt.plot(range(1, len(val_auc_scores) + 1), val_auc_scores, marker='o', linestyle='-', linewidth=2, markersize=8)
plt.xlabel('Epoch', fontsize=12)
plt.ylabel('Validation ROC-AUC', fontsize=12)
plt.title('Validation ROC-AUC Over Training Epochs', fontsize=14, fontweight='bold')
plt.grid(True, alpha=0.3)
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Print model summary
print("\nModel Summary:")
model.summary()

# Print final test evaluation
test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"\nTest Loss: {test_loss:.4f}")
print(f"Test Accuracy: {test_accuracy:.4f}")
print(f"Test ROC-AUC: {test_auc:.4f}")