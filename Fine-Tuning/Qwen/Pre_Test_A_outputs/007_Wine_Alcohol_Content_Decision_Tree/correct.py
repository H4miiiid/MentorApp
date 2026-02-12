import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error

# Set random seed for reproducibility
np.random.seed(42)

# Load the wine dataset
wine = load_wine()
X = wine.data
y = wine.data[:, 0]  # Alcohol is the first feature in the wine dataset

# Use all other features to predict alcohol content
X = wine.data[:, 1:]  # All features except alcohol

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Create and train the decision tree regressor
dt_regressor = DecisionTreeRegressor(random_state=42)
dt_regressor.fit(X_train, y_train)

# Make predictions on the test set
y_pred = dt_regressor.predict(X_test)

# Calculate RMSE
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")

# Plot predicted versus actual alcohol values
plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred, alpha=0.7, edgecolors='k')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
         'r--', lw=2, label='Perfect Prediction')
plt.xlabel('Actual Alcohol Content')
plt.ylabel('Predicted Alcohol Content')
plt.title('Decision Tree: Predicted vs Actual Alcohol Content')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Print summary statistics
print(f"\nNumber of training samples: {len(X_train)}")
print(f"Number of test samples: {len(X_test)}")
print(f"Mean actual alcohol content: {y_test.mean():.4f}")
print(f"Mean predicted alcohol content: {y_pred.mean():.4f}")
