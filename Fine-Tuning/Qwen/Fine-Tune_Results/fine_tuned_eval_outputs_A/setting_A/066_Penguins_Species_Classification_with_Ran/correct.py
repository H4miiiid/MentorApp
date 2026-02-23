import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

# Set random seed for reproducibility
np.random.seed(42)

# Load the penguins dataset from seaborn
penguins = sns.load_dataset('penguins')

# Drop rows with missing values
penguins = penguins.dropna()

# Separate features and target
X = penguins.drop('species', axis=1)
y = penguins['species']

# Encode categorical features
le_island = LabelEncoder()
le_sex = LabelEncoder()

X['island'] = le_island.fit_transform(X['island'])
X['sex'] = le_sex.fit_transform(X['sex'])

# Encode target variable
le_species = LabelEncoder()
y = le_species.fit_transform(y)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train a Random Forest classifier
rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
rf_classifier.fit(X_train, y_train)

# Make predictions on the test set
y_pred = rf_classifier.predict(X_test)

# Calculate and report accuracy
accuracy = accuracy_score(y_test, y_pred)
print(f"Random Forest Classifier Accuracy: {accuracy:.4f}")

# Get feature importances
feature_importances = rf_classifier.feature_importances_
feature_names = X.columns

# Create a DataFrame for feature importances
importances_df = pd.DataFrame({
    'feature': feature_names,
    'importance': feature_importances
}).sort_values(by='importance', ascending=False)

# Get the top 3 important features
top_3_features = importances_df.head(3)

print("\nTop 3 Important Features:")
print(top_3_features)

# Plot the top 3 important features
plt.figure(figsize=(10, 6))
plt.barh(top_3_features['feature'], top_3_features['importance'], color='skyblue')
plt.xlabel('Importance')
plt.ylabel('Feature')
plt.title('Top 3 Important Features for Penguins Species Classification')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
