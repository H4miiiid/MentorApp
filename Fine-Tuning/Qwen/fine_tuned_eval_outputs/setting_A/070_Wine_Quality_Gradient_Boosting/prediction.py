import numpy as np

import matplotlib.pyplot as plt
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error

# Set random seed for reproducibility
np.random.seed(42)

# Load the wine dataset from scikit-learn
wine = load_wine()
X = wine.data
y = wine.target  # Using target as a regression target (quality proxy)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("Wine Quality Gradient Boosting")
print("=" * 50)
print(f"Dataset shape: {X.shape}")
print(f"Training set size: {X_train.shape[0]}")
print(f"Test set size: {X_test.shape[0]}")
print(f"Number of features: {X.shape[1]}")
print()

# Train a baseline GradientBoostingRegressor
print("Training baseline GradientBoostingRegressor...")
baseline_model = GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=3,
    random_state=42
)
baseline_model.fit(X_train, y_train)

# Evaluate the baseline model
y_pred_baseline = baseline_model.predict(X_test)
rmse_baseline = np.sqrt(mean_squared_error(y_test, y_pred_baseline))
print(f"Baseline RMSE: {rmse_baseline:.4f}")
print()

# Hyperparameter sweep over learning rate
print("Performing hyperparameter sweep over learning rate...")
learning_rates = [0.01, 0.05, 0.1, 0.2, 0.5]
rmse_scores = []

for lr in learning_rates:
    model = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=lr,
        max_depth=3,
        random_state=42
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    rmse_scores.append(rmse)
    print(f"Learning rate: {lr:.2f}, RMSE: {rmse:.4f}")

# Find the best learning rate
best_idx = np.argmin(rmse_scores)
best_lr = learning_rates[best_idx]
best_rmse = rmse_scores[best_idx]
print()
print(f"Best learning rate: {best_lr:.2f} with RMSE: {best_rmse:.4f}")
print()

# Train the final model with the best learning rate
print("Training final model with best learning rate...")
final_model = GradientBoostingRegressor(
    n_estimators=100,
    learning_rate=best_lr,
    max_depth=3,
    random_state=42
)
final_model.fit(X_train, y_train)

# Evaluate the final model
y_pred_final = final_model.predict(X_test)
rmse_final = np.sqrt(mean_squared_error(y_test, y_pred_final))
print(f"Final model RMSE: {rmse_final:.4f}")
print()

# Plot feature importance
feature_importance = final_model.feature_importances_
feature_names = wine.feature_names

# Sort features by importance
indices = np.argsort(feature_importance)[::-1]

plt.figure(figsize=(10, 6))
plt.bar(range(len(feature_importance)), feature_importance[indices])
plt.xticks(range(len(feature_importance)), [feature_names[i] for i in indices], rotation=45, ha='right')
plt.xlabel('Features')
plt.ylabel('Importance')
plt.title('Feature Importance - Gradient Boosting Regressor')
plt.tight_layout()
plt.show()

# Plot learning rate vs RMSE
plt.figure(figsize=(8, 5))
plt.plot(learning_rates, rmse_scores, marker='o', linestyle='-', linewidth=2, markersize=8)
plt.xlabel('Learning Rate')
plt.ylabel('RMSE')
plt.title('Hyperparameter Sweep: Learning Rate vs RMSE')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print("\nTop 5 most important features:")
for i in range(min(5, len(feature_names))):
    idx = indices[i]
    print(f"{i+1}. {feature_names[idx]}: {feature_importance[idx]:.4f}")