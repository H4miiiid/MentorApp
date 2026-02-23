import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import BaggingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns

# Load the breast cancer dataset
data = load_breast_cancer()
X = data.data
y = data.target

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Dataset Information:")
print(f"Number of samples: {X.shape[0]}")
print(f"Number of features: {X.shape[1]}")
print(f"Target classes: {data.target_names}")
print(f"Training set size: {X_train.shape[0]}")
print(f"Test set size: {X_test.shape[0]}")
print("\n" + "="*60 + "\n")

# Build a single decision tree classifier
print("Training Single Decision Tree...")
single_tree = DecisionTreeClassifier(random_state=42)
single_tree.fit(X_train, y_train)

# Make predictions with single tree
y_pred_single = single_tree.predict(X_test)
single_tree_accuracy = accuracy_score(y_test, y_pred_single)

print(f"Single Decision Tree Accuracy: {single_tree_accuracy:.4f}")
print("\n" + "="*60 + "\n")

# Build a bagging ensemble of decision trees
print("Training Bagging Ensemble (with OOB estimation)...")
bagging_clf = BaggingClassifier(
    estimator=DecisionTreeClassifier(random_state=42),
    n_estimators=100,
    max_samples=1.0,
    max_features=1.0,
    bootstrap=True,
    oob_score=True,
    random_state=42,
    n_jobs=-1
)
bagging_clf.fit(X_train, y_train)

# Make predictions with bagging ensemble
y_pred_bagging = bagging_clf.predict(X_test)
bagging_accuracy = accuracy_score(y_test, y_pred_bagging)

print(f"Bagging Ensemble Accuracy: {bagging_accuracy:.4f}")
print(f"Out-of-Bag (OOB) Score: {bagging_clf.oob_score_:.4f}")
print("\n" + "="*60 + "\n")

# Compare the two models
print("Model Comparison:")
print(f"Single Decision Tree Accuracy: {single_tree_accuracy:.4f}")
print(f"Bagging Ensemble Accuracy: {bagging_accuracy:.4f}")
print(f"Improvement: {(bagging_accuracy - single_tree_accuracy):.4f}")
print(f"\nOOB Error Estimate: {(1 - bagging_clf.oob_score_):.4f}")
print("\n" + "="*60 + "\n")

# Detailed classification report for bagging ensemble
print("Classification Report (Bagging Ensemble):")
print(classification_report(y_test, y_pred_bagging, target_names=data.target_names))

# Visualize confusion matrix for bagging ensemble
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Confusion matrix for single tree
cm_single = confusion_matrix(y_test, y_pred_single)
sns.heatmap(cm_single, annot=True, fmt='d', cmap='Blues', ax=axes[0],
            xticklabels=data.target_names, yticklabels=data.target_names)
axes[0].set_title(f'Single Decision Tree\nAccuracy: {single_tree_accuracy:.4f}')
axes[0].set_ylabel('True Label')
axes[0].set_xlabel('Predicted Label')

# Confusion matrix for bagging ensemble
cm_bagging = confusion_matrix(y_test, y_pred_bagging)
sns.heatmap(cm_bagging, annot=True, fmt='d', cmap='Greens', ax=axes[1],
            xticklabels=data.target_names, yticklabels=data.target_names)
axes[1].set_title(f'Bagging Ensemble\nAccuracy: {bagging_accuracy:.4f}')
axes[1].set_ylabel('True Label')
axes[1].set_xlabel('Predicted Label')

plt.tight_layout()
plt.savefig('confusion_matrices.png', dpi=100, bbox_inches='tight')
plt.show()

# Visualize accuracy comparison
fig, ax = plt.subplots(figsize=(10, 6))
models = ['Single Decision Tree', 'Bagging Ensemble']
accuracies = [single_tree_accuracy, bagging_accuracy]
colors = ['skyblue', 'lightgreen']

bars = ax.bar(models, accuracies, color=colors, edgecolor='black', linewidth=1.5)
ax.set_ylabel('Accuracy', fontsize=12)
ax.set_title('Model Accuracy Comparison', fontsize=14, fontweight='bold')
ax.set_ylim([0.9, 1.0])
ax.axhline(y=bagging_clf.oob_score_, color='red', linestyle='--', 
           label=f'OOB Score: {bagging_clf.oob_score_:.4f}')

# Add value labels on bars
for bar, acc in zip(bars, accuracies):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{acc:.4f}',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('accuracy_comparison.png', dpi=100, bbox_inches='tight')
plt.show()

print("\nVisualization complete. Plots saved as 'confusion_matrices.png' and 'accuracy_comparison.png'.")