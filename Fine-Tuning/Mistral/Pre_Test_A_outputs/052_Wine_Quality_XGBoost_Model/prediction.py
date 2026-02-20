import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import xgboost as xgb

# Set random seed for reproducibility
np.random.seed(42)

# Load the wine dataset from scikit-learn
wine_data = load_wine()
X = wine_data.data
y = wine_data.target
feature_names = wine_data.feature_names

# Split data into train, validation, and test sets
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.3, random_state=42
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, random_state=42
)

print(f"Training set size: {X_train.shape[0]}")
print(f"Validation set size: {X_val.shape[0]}")
print(f"Test set size: {X_test.shape[0]}")

# Create XGBoost classifier (not regressor) since wine dataset is classification
model = xgb.XGBClassifier(
    n_estimators=1000,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    early_stopping_rounds=10
)

# Train the model with early stopping on validation set
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)

print(f"\nBest iteration: {model.best_iteration}")

# Make predictions on test set
y_pred = model.predict(X_test)

# Evaluate performance with accuracy (not RMSE for classification)
from sklearn.metrics import accuracy_score
accuracy = accuracy_score(y_test, y_pred)
print(f"\nTest Accuracy: {accuracy:.4f}")

# Plot feature importance
fig, ax = plt.subplots(figsize=(10, 6))
importances = model.feature_importances_
indices = np.argsort(importances)[::-1]

ax.bar(range(len(importances)), importances[indices])
ax.set_xlabel('Feature Index', fontsize=12)
ax.set_ylabel('Feature Importance', fontsize=12)
ax.set_title('XGBoost Feature Importance for Wine Classification', fontsize=14)
ax.set_xticks(range(len(importances)))
ax.set_xticklabels([feature_names[i] for i in indices], rotation=45, ha='right')
plt.tight_layout()
plt.show()

# Display top 5 most important features
print("\nTop 5 Most Important Features:")
for i in range(min(5, len(importances))):
    idx = indices[i]
    print(f"{i+1}. {feature_names[idx]}: {importances[idx]:.4f}")

# Display sample predictions vs actual values
print("\nSample Predictions vs Actual Values (first 10 test samples):")
for i in range(min(10, len(y_test))):
    print(f"Actual: {y_test[i]}, Predicted: {y_pred[i]}")