import numpy as np

import matplotlib.pyplot as plt
from sklearn.datasets import load_diabetes
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error
import lightgbm as lgb

# Set random seed for reproducibility
np.random.seed(42)

# Load the California housing dataset
data = load_diabetes()
X = data.data
y = data.target

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print("California Housing Dataset Loaded")
print(f"Training samples: {X_train.shape[0]}")
print(f"Testing samples: {X_test.shape[0]}")
print(f"Number of features: {X_train.shape[1]}")
print()

# Train a LightGBM regressor with default parameters
print("Training LightGBM regressor with default parameters...")
lgb_default = lgb.LGBMRegressor(random_state=42, verbose=-1)
lgb_default.fit(X_train, y_train)

# Make predictions with default model
y_pred_default = lgb_default.predict(X_test)

# Calculate RMSE for default model
rmse_default = np.sqrt(mean_squared_error(y_test, y_pred_default))
print(f"Default Model RMSE: {rmse_default:.4f}")
print()

# Fine-tune leaf count (num_leaves) and learning rate
print("Fine-tuning hyperparameters (num_leaves and learning_rate)...")
param_grid = {
    'num_leaves': [20, 31, 40],
    'learning_rate': [0.05, 0.1, 0.2]
}

# Use GridSearchCV for hyperparameter tuning
grid_search = GridSearchCV(
    estimator=lgb.LGBMRegressor(random_state=42, verbose=-1),
    param_grid=param_grid,
    cv=3,
    scoring='neg_mean_squared_error',
    n_jobs=-1,
    verbose=0
)

grid_search.fit(X_train, y_train)

# Get the best model
lgb_tuned = grid_search.best_estimator_
print(f"Best parameters: {grid_search.best_params_}")

# Make predictions with tuned model
y_pred_tuned = lgb_tuned.predict(X_test)

# Calculate RMSE for tuned model
rmse_tuned = np.sqrt(mean_squared_error(y_test, y_pred_tuned))
print(f"Tuned Model RMSE: {rmse_tuned:.4f}")
print()

# Report improvement
improvement = ((rmse_default - rmse_tuned) / rmse_default) * 100
print(f"RMSE improvement: {improvement:.2f}%")
print()

# Visualize predicted vs. actual values for both models
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot for default model
axes[0].scatter(y_test, y_pred_default, alpha=0.5, s=10)
axes[0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
             'r--', lw=2, label='Perfect prediction')
axes[0].set_xlabel('Actual Values')
axes[0].set_ylabel('Predicted Values')
axes[0].set_title(f'Default Model\nRMSE: {rmse_default:.4f}')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Plot for tuned model
axes[1].scatter(y_test, y_pred_tuned, alpha=0.5, s=10, color='green')
axes[1].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
             'r--', lw=2, label='Perfect prediction')
axes[1].set_xlabel('Actual Values')
axes[1].set_ylabel('Predicted Values')
axes[1].set_title(f'Tuned Model\nRMSE: {rmse_tuned:.4f}')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('california_housing_lightgbm_predictions.png', dpi=100, bbox_inches='tight')
plt.show()

print("Visualization saved as 'california_housing_lightgbm_predictions.png'")
print("\nProject completed successfully!")