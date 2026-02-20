
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score

# Set random seed for reproducibility
np.random.seed(42)

# Load the Titanic dataset from seaborn
titanic = sns.load_dataset('titanic')

# Select relevant features and target
# We'll use a subset of features that are commonly used for prediction
features = ['pclass', 'sex', 'age', 'sibsp', 'parch', 'fare']
target = 'survived'

# Create a copy of the dataset with selected features
df = titanic[features + [target]].copy()

# Convert categorical variables to numeric
df['sex'] = df['sex'].map({'male': 0, 'female': 1})

# Drop rows with missing target values
df = df.dropna(subset=[target])

# Separate features and target
X = df[features]
y = df[target]

# Split data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ===== BEFORE IMPUTATION =====
# For the "before" case, we'll drop rows with missing age values
X_train_before = X_train.dropna()
y_train_before = y_train.loc[X_train_before.index]

X_test_before = X_test.dropna()
y_test_before = y_test.loc[X_test_before.index]

# Train decision tree classifier without imputation
dt_before = DecisionTreeClassifier(random_state=42)
dt_before.fit(X_train_before, y_train_before)

# Predict and calculate accuracy
y_pred_before = dt_before.predict(X_test_before)
accuracy_before = accuracy_score(y_test_before, y_pred_before)

print(f"Accuracy before imputation: {accuracy_before:.4f}")

# ===== AFTER IMPUTATION =====
# Calculate median age from training data
median_age = X_train['age'].median()

# Impute missing ages with median
X_train_after = X_train.copy()
X_train_after['age'] = X_train_after['age'].fillna(median_age)

X_test_after = X_test.copy()
X_test_after['age'] = X_test_after['age'].fillna(median_age)

# Handle any remaining missing values in other columns by filling with median
for col in X_train_after.columns:
    if X_train_after[col].isnull().any():
        col_median = X_train_after[col].median()
        X_train_after[col] = X_train_after[col].fillna(col_median)
        X_test_after[col] = X_test_after[col].fillna(col_median)

# Train decision tree classifier with imputation
dt_after = DecisionTreeClassifier(random_state=42)
dt_after.fit(X_train_after, y_train)

# Predict and calculate accuracy
y_pred_after = dt_after.predict(X_test_after)
accuracy_after = accuracy_score(y_test, y_pred_after)

print(f"Accuracy after imputation: {accuracy_after:.4f}")

# Calculate the difference in accuracy
accuracy_diff = abs(accuracy_after - accuracy_before)
print(f"Absolute difference in accuracy: {accuracy_diff:.4f}")

# Verify that the change is less than 1% (0.01)
if accuracy_diff < 0.01:
    print("✓ The change in accuracy is less than 1%.")
else:
    print(f"Note: The change in accuracy ({accuracy_diff:.4f}) is >= 1%.")

# Summary
print("\n=== Summary ===")
print(f"Test accuracy before imputation: {accuracy_before:.4f}")
print(f"Test accuracy after imputation: {accuracy_after:.4f}")
print(f"Difference: {accuracy_diff:.4f}")