import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error

# Set random seed for reproducibility
np.random.seed(42)

# Load the wine dataset
wine = load_wine()
X = wine.data
y = wine.target[:, 0]  # Using only alcohol content (first column) as target

# Use the remaining features to predict alcohol content
X_features = wine.data[:, 1:]  # All features except alcohol

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X_features, y, test_size=0.2, random_state=42
)

# Standardize the features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train a Support Vector Regressor
svr = SVR(kernel='rbf', C=100, gamma=0.1)
svr.fit(X_train_scaled, y_train)

# Make predictions on the test set
y_pred = svr.predict(X_test_scaled)

# Calculate RMSE
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"Root Mean Squared Error (RMSE): {rmse:.4f}")

# Plot predicted versus true alcohol values
plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred, alpha=0.7, edgecolors='k')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2, label='Perfect Prediction')
plt.xlabel('True Alcohol Content')
plt.ylabel('Predicted Alcohol Content')
plt.title('SVR: Predicted vs True Alcohol Content')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Print sample predictions
print("\nSample Predictions (first 10 test samples):")
for i in range(min(10, len(y_test))):
    print(f"True: {y_test[i]:.2f}, Predicted: {y_pred[i]:.2f}")