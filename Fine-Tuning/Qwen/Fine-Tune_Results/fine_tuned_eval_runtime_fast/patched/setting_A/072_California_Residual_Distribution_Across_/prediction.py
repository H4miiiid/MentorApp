
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import fetch_california_housing
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

# Set random seed for reproducibility
np.random.seed(42)

# Load the California housing dataset
data = fetch_california_housing()
X = data.data
y = data.target

# Initialize Ridge regression model
ridge_model = Ridge(alpha=1.0, random_state=42)

# Set up 5-fold cross-validation
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# Collect residuals for each fold
residuals_per_fold = []

for fold_idx, (train_index, test_index) in enumerate(kf.split(X)):
    # Split data into train and test for this fold
    X_train, X_test = X[train_index], X[test_index]
    y_train, y_test = y[train_index], y[test_index]

    # Train the Ridge model
    ridge_model.fit(X_train, y_train)

    # Predict on test set
    y_pred = ridge_model.predict(X_test)

    # Calculate residuals (actual - predicted)
    residuals = y_test - y_pred
    residuals_per_fold.append(residuals)

# Plot residual histograms side by side
fig, axes = plt.subplots(1, 5, figsize=(20, 4))
fig.suptitle('Residual Distribution Across 5 Folds (California Housing)', fontsize=16)

for i, (ax, residuals) in enumerate(zip(axes, residuals_per_fold)):
    ax.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
    ax.set_title(f'Fold {i+1}')
    ax.set_xlabel('Residuals')
    ax.set_ylabel('Frequency')
    ax.grid(True, alpha=0.3)

plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Print summary statistics for each fold
print("\nResidual Statistics Across Folds:")
print("="*60)
for i, residuals in enumerate(residuals_per_fold):
    print(f"Fold {i+1}:")
    print(f"  Mean: {np.mean(residuals):.4f}")
    print(f"  Std Dev: {np.std(residuals):.4f}")
    print(f"  Min: {np.min(residuals):.4f}")
    print(f"  Max: {np.max(residuals):.4f}")
    print()