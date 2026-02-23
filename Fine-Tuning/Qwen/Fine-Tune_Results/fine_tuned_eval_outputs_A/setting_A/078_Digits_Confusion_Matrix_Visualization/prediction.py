import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# Set random seed for reproducibility
np.random.seed(42)

# Load the digits dataset
digits = load_digits()
X = digits.data
y = digits.target

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# Train a Support Vector Machine classifier
print("Training SVM classifier...")
svm_classifier = SVC(kernel='rbf', gamma='scale', random_state=42)
svm_classifier.fit(X_train, y_train)

# Make predictions on the test set
y_pred = svm_classifier.predict(X_test)

# Calculate accuracy
accuracy = np.mean(y_pred == y_test)
print(f"Test set accuracy: {accuracy:.4f}")

# Generate confusion matrix
cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(cm)

# Visualize the confusion matrix with a heatmap
fig, ax = plt.subplots(figsize=(10, 8))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=digits.target_names)
disp.plot(cmap='Blues', ax=ax, colorbar=True)
plt.title('Confusion Matrix for Digits Classification', fontsize=14, fontweight='bold')
plt.xlabel('Predicted Label', fontsize=12)
plt.ylabel('True Label', fontsize=12)
plt.tight_layout()
plt.show()

# Identify and interpret the most common misclassifications
print("\n=== Analysis of Misclassifications ===")

# Create a copy of the confusion matrix with diagonal set to 0 to find misclassifications
cm_errors = cm.copy()
np.fill_diagonal(cm_errors, 0)

# Find the top 5 most common misclassifications
top_n = 5
flat_indices = np.argsort(cm_errors.ravel())[::-1][:top_n]
top_misclassifications = np.unravel_index(flat_indices, cm_errors.shape)

print(f"\nTop {top_n} most common misclassifications:")
for i in range(top_n):
    true_label = top_misclassifications[0][i]
    pred_label = top_misclassifications[1][i]
    count = cm_errors[true_label, pred_label]
    if count > 0:
        print(f"{i+1}. True label: {true_label}, Predicted as: {pred_label}, Count: {count}")

# Calculate per-class accuracy
print("\nPer-class accuracy:")
for i in range(len(digits.target_names)):
    class_total = np.sum(cm[i, :])
    class_correct = cm[i, i]
    if class_total > 0:
        class_accuracy = class_correct / class_total
        print(f"Digit {i}: {class_accuracy:.4f} ({class_correct}/{class_total})")

# Summary statistics
total_predictions = np.sum(cm)
correct_predictions = np.trace(cm)
incorrect_predictions = total_predictions - correct_predictions

print("\n=== Summary ===")
print(f"Total test samples: {total_predictions}")
print(f"Correct predictions: {correct_predictions}")
print(f"Incorrect predictions: {incorrect_predictions}")
print(f"Overall accuracy: {accuracy:.4f}")