
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix, ConfusionMatrixDisplay

# Set random seed for reproducibility
np.random.seed(42)

# Load the wine dataset
wine = load_wine()
X = wine.data
y = wine.target

# Transform the target into binary labels using threshold of 6
# The wine dataset has targets 0, 1, 2 representing different wine classes
# We interpret the target values as quality scores and apply threshold
# Values >= 6 are considered "good" (1), otherwise "not good" (0)
# Since original targets are 0, 1, 2, we need to map them to quality scores
# We'll treat class 2 as high quality (>=6) and classes 0,1 as lower quality (<6)
y_binary = (y == 2).astype(int)  # Fixed: Changed >= to == since targets are 0,1,2

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y_binary, test_size=0.3, random_state=42, stratify=y_binary
)

# Train a logistic regression model
model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X_train, y_train)

# Make predictions on the test set
y_pred = model.predict(X_test)

# Calculate and report metrics
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)

print("Wine Quality Binary Classification Results")
print("="*50)
print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print()

# Compute confusion matrix
cm = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:")
print(cm)
print()

# Plot the confusion matrix
fig, ax = plt.subplots(figsize=(8, 6))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Not Good', 'Good'])
disp.plot(ax=ax, cmap='Blues', values_format='d')
plt.title('Confusion Matrix for Wine Quality Classification')
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

print("\nModel training and evaluation complete!")