
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error

# Set random seed for reproducibility
np.random.seed(42)

# Load the tips dataset from seaborn
tips = sns.load_dataset('tips')

# Display basic information about the dataset
print("Tips Dataset Shape:", tips.shape)
print("\nFirst few rows:")
print(tips.head())
print("\nDataset Info:")
print(tips.info())

# Prepare features and target
# Target variable: tip
y = tips['tip'].values

# Features: numeric columns (total_bill, size) and encoded categorical columns
# We'll use one-hot encoding for categorical variables
X = tips.drop('tip', axis=1)

# One-hot encode categorical variables
X_encoded = pd.get_dummies(X, columns=['sex', 'smoker', 'day', 'time'], drop_first=True)

print("\nFeatures after encoding:")
print(X_encoded.head())
print("\nFeature columns:", X_encoded.columns.tolist())

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X_encoded, y, test_size=0.2, random_state=42
)

print("\nTraining set size:", X_train.shape[0])
print("Testing set size:", X_test.shape[0])

# Scale numeric features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train a Linear Regression model
model = LinearRegression()
model.fit(X_train_scaled, y_train)

print("\nModel trained successfully.")
print("Model coefficients shape:", model.coef_.shape)
print("Model intercept:", model.intercept_)

# Make predictions on the test set
y_pred = model.predict(X_test_scaled)

# Calculate Mean Absolute Error
mae = mean_absolute_error(y_test, y_pred)
print("\nMean Absolute Error (MAE):", round(mae, 4))

# Create a scatter plot of predicted vs. actual tips
plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred, alpha=0.6, edgecolors='k', linewidth=0.5)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 
         'r--', lw=2, label='Perfect Prediction')
plt.xlabel('Actual Tip Amount ($)', fontsize=12)
plt.ylabel('Predicted Tip Amount ($)', fontsize=12)
plt.title('Predicted vs. Actual Tip Amounts', fontsize=14, fontweight='bold')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

print("\nModel evaluation complete.")
print(f"The model achieves a Mean Absolute Error of ${mae:.4f} on the test set.")