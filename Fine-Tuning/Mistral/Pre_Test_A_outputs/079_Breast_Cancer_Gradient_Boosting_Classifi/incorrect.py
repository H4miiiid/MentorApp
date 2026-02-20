import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

# Set random seed for reproducibility
np.random.seed(42)

# Load the breast cancer dataset
data = load_breast_cancer()
X = data.data
y = data.target
feature_names = data.feature_names

# Create a GradientBoostingClassifier
gb_classifier = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)

# Perform 5-fold cross-validation and compute ROC-AUC scores
roc_auc_scores = cross_val_score(gb_classifier, X, y, cv=1, scoring='roc_auc')

# Print cross-validation results
print("5-Fold Cross-Validation ROC-AUC Scores:")
for i, score in enumerate(roc_auc_scores, 1):
    print(f"Fold {i}: {score:.4f}")
print(f"\nMean ROC-AUC: {roc_auc_scores.mean():.4f}")
print(f"Standard Deviation: {roc_auc_scores.std():.4f}")

# Train the model on the entire dataset for feature importance visualization
gb_classifier.fit(X, y)

# Get feature importances
feature_importances = gb_classifier.feature_importances_

# Create a DataFrame for better visualization
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': feature_importances
}).sort_values('importance', ascending=False)

# Display top 10 most important features
print("\nTop 10 Most Important Features:")
print(importance_df.head(10).to_string(index=False))

# Visualize feature importance
plt.figure(figsize=(10, 8))
top_n = 15
top_features = importance_df.head(top_n)
plt.barh(range(top_n), top_features['importance'].values)
plt.yticks(range(top_n), top_features['feature'].values)
plt.xlabel('Feature Importance')
plt.ylabel('Feature')
plt.title(f'Top {top_n} Feature Importances - Gradient Boosting Classifier')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()

# Make predictions on the training set to demonstrate model usage
y_pred_proba = gb_classifier.predict_proba(X)[:, 1]
train_roc_auc = roc_auc_score(y, y_pred_proba)
print(f"\nTraining Set ROC-AUC: {train_roc_auc:.4f}")