
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Set random seed for reproducibility
np.random.seed(42)

# Load MNIST dataset from keras
(X_train_full, y_train_full), (X_test, y_test) = keras.datasets.mnist.load_data()

# Flatten images from 28x28 to 784-dimensional vectors
X_train_full = X_train_full.reshape(X_train_full.shape[0], -1)
X_test = X_test.reshape(X_test.shape[0], -1)

# Normalize pixel values to [0, 1]
X_train_full = X_train_full.astype('float32') / 255.0
X_test = X_test.astype('float32') / 255.0

# Use a subset of training data for faster runtime
# (KNN can be slow on large datasets)
X_train, _, y_train, _ = train_test_split(
    X_train_full, y_train_full, train_size=5000, random_state=42, stratify=y_train_full
)

# Create and train KNN classifier with k=3
print("Training KNN classifier with k=3...")
knn = KNeighborsClassifier(n_neighbors=3)
knn.fit(X_train, y_train)

# Make predictions on test set subset
y_pred = knn.predict(X_test)

# Evaluate accuracy on the subset
accuracy = accuracy_score(y_test, y_pred)
print(f"Test Accuracy: {accuracy:.4f}")

# Find correctly and incorrectly classified examples
correct_indices = np.where(y_pred == y_test)[0]
incorrect_indices = np.where(y_pred != y_test)[0]

# Display a few correctly classified images
num_correct_to_show = min(3, len(correct_indices))
if num_correct_to_show > 0:
    fig, axes = plt.subplots(1, num_correct_to_show, figsize=(12, 4))
    fig.suptitle('Correctly Classified Images', fontsize=14)
    if num_correct_to_show == 1:
        axes = [axes]
    for i in range(num_correct_to_show):
        idx = correct_indices[i]
        img = X_test[idx].reshape(28, 28)
        axes[i].imshow(img, cmap='gray')
        axes[i].set_title(f'True: {y_test[idx]}, Pred: {y_pred[idx]}')
        axes[i].axis('off')
    plt.tight_layout()
    print('[FAST_EVAL] plt.show() skipped')

# Display a few incorrectly classified images
num_incorrect_to_show = min(3, len(incorrect_indices))
if num_incorrect_to_show > 0:
    fig, axes = plt.subplots(1, num_incorrect_to_show, figsize=(12, 4))
    fig.suptitle('Incorrectly Classified Images', fontsize=14)
    if num_incorrect_to_show == 1:
        axes = [axes]
    for i in range(num_incorrect_to_show):
        idx = incorrect_indices[i]
        img = X_test[idx].reshape(28, 28)
        axes[i].imshow(img, cmap='gray')
        axes[i].set_title(f'True: {y_test[idx]}, Pred: {y_pred[idx]}')
        axes[i].axis('off')
    plt.tight_layout()
    print('[FAST_EVAL] plt.show() skipped')
else:
    print("No incorrectly classified images found (perfect accuracy).")

print("\nMNIST KNN classification complete.")