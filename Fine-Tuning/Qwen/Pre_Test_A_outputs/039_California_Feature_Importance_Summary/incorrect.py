import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import fetch_california_housing
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

# Load the California housing dataset
data = fetch_california_housing()
X = data.data
y = data.target
feature_names = data.feature_names

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=1.5, random_state=42)

# Create and fit a GradientBoostingRegressor
model = GradientBoostingRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Extract feature importances
feature_importances = model.feature_importances_

# Create a list of (feature_name, importance) tuples and sort by importance
feature_importance_pairs = list(zip(feature_names, feature_importances))
feature_importance_pairs_sorted = sorted(feature_importance_pairs, key=lambda x: x[1], reverse=True)

# Get the top 5 features
top_5_features = feature_importance_pairs_sorted[:5]
top_5_names = [item[0] for item in top_5_features]
top_5_importances = [item[1] for item in top_5_features]

# Create a horizontal bar chart
plt.figure(figsize=(10, 6))
plt.barh(top_5_names, top_5_importances, color='steelblue')
plt.xlabel('Feature Importance')
plt.ylabel('Feature')
plt.title('Top 5 Feature Importances for California Housing Price Prediction')
plt.gca().invert_yaxis()  # Highest importance at the top
plt.tight_layout()
plt.show()

# Print the top 5 features and their importances
print("Top 5 Feature Importances:")
for i, (name, importance) in enumerate(top_5_features, 1):
    print(f"{i}. {name}: {importance:.4f}")