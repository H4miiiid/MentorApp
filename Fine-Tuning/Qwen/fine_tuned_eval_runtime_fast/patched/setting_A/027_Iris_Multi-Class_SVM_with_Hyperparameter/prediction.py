
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, accuracy_score

# Set random seed for reproducibility
np.random.seed(42)

# Load the iris dataset
iris = load_iris()
X = iris.data
y = iris.target

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# Define the parameter grid for grid search
# We search over C (regularization parameter) and gamma (kernel coefficient)
param_grid = {
    'C': [0.1, 1, 10, 100],
    'gamma': [0.001, 0.01, 0.1, 1, 'scale', 'auto']
}

# Create the SVM classifier with RBF kernel
svm_model = SVC(kernel='rbf', random_state=42)

# Perform grid search with cross-validation
# Using 5-fold cross-validation by default
grid_search = GridSearchCV(
    estimator=svm_model,
    param_grid=param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    verbose=0
)

# Fit the grid search to the training data
print("Performing grid search over C and gamma...")
grid_search.fit(X_train, y_train)

# Report the best parameters and best cross-validated accuracy
print("\nBest parameters found:")
print(f"  C: {grid_search.best_params_['C']}")
print(f"  gamma: {grid_search.best_params_['gamma']}")
print(f"\nBest cross-validated accuracy: {grid_search.best_score_:.4f}")

# Get the best model from grid search
best_svm = grid_search.best_estimator_

# Make predictions on the test set
y_pred = best_svm.predict(X_test)

# Calculate test accuracy
test_accuracy = accuracy_score(y_test, y_pred)
print(f"Test set accuracy: {test_accuracy:.4f}")

# Compute the confusion matrix
cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(cm)

# Display the confusion matrix as a heatmap
fig, ax = plt.subplots(figsize=(8, 6))
disp = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=iris.target_names
)
disp.plot(cmap='Blues', ax=ax, values_format='d')
plt.title('Confusion Matrix for Tuned SVM (RBF Kernel)')
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

print("\nMulti-class SVM with hyperparameter tuning completed successfully.")