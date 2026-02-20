
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix

# Load the breast cancer dataset
data = load_breast_cancer()
X = data.data
y = data.target

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

# Perform standard scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train SVM with RBF kernel
svm_model = SVC(kernel='rbf', probability=True, random_state=42)
svm_model.fit(X_train_scaled, y_train)

# Train logistic regression baseline
lr_model = LogisticRegression(max_iter=10000, random_state=42)
lr_model.fit(X_train_scaled, y_train)

# Make predictions
svm_pred = svm_model.predict(X_test_scaled)
lr_pred = lr_model.predict(X_test_scaled)

# Get probability predictions for ROC-AUC
svm_pred_proba = svm_model.predict_proba(X_test_scaled)[:, 1]
lr_pred_proba = lr_model.predict_proba(X_test_scaled)[:, 1]

# Evaluate with ROC-AUC
svm_roc_auc = roc_auc_score(y_test, svm_pred_proba)
lr_roc_auc = roc_auc_score(y_test, lr_pred_proba)

print("SVM Classifier Results:")
print(f"ROC-AUC Score: {svm_roc_auc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, svm_pred, target_names=data.target_names))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, svm_pred))

print("\n" + "="*50)
print("\nLogistic Regression Baseline Results:")
print(f"ROC-AUC Score: {lr_roc_auc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, lr_pred, target_names=data.target_names))
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, lr_pred))

print("\n" + "="*50)
print(f"\nComparison: SVM ROC-AUC ({svm_roc_auc:.4f}) vs Logistic Regression ROC-AUC ({lr_roc_auc:.4f})")

# Plot decision function for two selected features
# Select two features for visualization (mean radius and mean texture)
feature_indices = [0, 1]  # mean radius and mean texture
feature_names = [data.feature_names[i] for i in feature_indices]

# Extract the two features
X_train_2d = X_train_scaled[:, feature_indices]
X_test_2d = X_test_scaled[:, feature_indices]

# Train a new SVM on just these two features for visualization
svm_2d = SVC(kernel='rbf', probability=True, random_state=42)
svm_2d.fit(X_train_2d, y_train)

# Create a mesh to plot decision boundaries
h = 0.02  # step size in the mesh
x_min, x_max = X_train_2d[:, 0].min() - 1, X_train_2d[:, 0].max() + 1
y_min, y_max = X_train_2d[:, 1].min() - 1, X_train_2d[:, 1].max() + 1
xx, yy = np.meshgrid(np.arange(x_min, x_max, h), np.arange(y_min, y_max, h))

# Compute decision function values
Z = svm_2d.decision_function(np.c_[xx.ravel(), yy.ravel()])
Z = Z.reshape(xx.shape)

# Plot decision function and data points
plt.figure(figsize=(12, 5))

# Plot 1: Decision function contours (Training Data)
plt.subplot(1, 2, 1)
plt.contourf(xx, yy, Z, levels=20, cmap='RdYlBu', alpha=0.8)
plt.colorbar(label='Decision Function')
plt.contour(xx, yy, Z, levels=[0], linewidths=2, colors='black')
plt.scatter(X_train_2d[:, 0], X_train_2d[:, 1], c=y_train, cmap='RdYlBu', edgecolors='k', s=50, alpha=0.7)
plt.xlabel(feature_names[0])
plt.ylabel(feature_names[1])
plt.title('SVM Decision Function (Training Data)')
plt.grid(True, alpha=0.3)

# Plot 2: Test data predictions
plt.subplot(1, 2, 2)
plt.contourf(xx, yy, Z, levels=20, cmap='RdYlBu', alpha=0.8)
plt.colorbar(label='Decision Function')
plt.contour(xx, yy, Z, levels=[0], linewidths=2, colors='black')
plt.scatter(X_test_2d[:, 0], X_test_2d[:, 1], c=svm_2d.predict(np.c_[xx.ravel(), yy.ravel()]), cmap='RdYlBu', edgecolors='k', s=50, alpha=0.7)
plt.xlabel(feature_names[0])
plt.ylabel(feature_names[1])
plt.title('SVM Decision Function (Test Data)')
plt.grid(True, alpha=0.3)

plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

print("\nVisualization complete. The decision boundary is shown as a black contour line.")
print(f"The SVM with RBF kernel achieved a ROC-AUC of {svm_roc_auc:.4f} on the full feature set.")
print(f"The Logistic Regression baseline achieved a ROC-AUC of {lr_roc_auc:.4f}.")