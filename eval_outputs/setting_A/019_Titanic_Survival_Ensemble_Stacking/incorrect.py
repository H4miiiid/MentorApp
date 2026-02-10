import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, StackingClassifier
from sklearn.metrics import accuracy_score

# Set random seed for reproducibility
np.random.seed(42)

# Load the Titanic dataset from seaborn
titanic = sns.load_dataset('titanic')

# Select relevant features for modeling
# We'll use: pclass, sex, age, sibsp, parch, fare, embarked
features = ['pclass', 'sex', 'age', 'sibsp', 'parch', 'fare', 'embarked']
target = 'survived'

# Create a working dataframe with selected features and target
df = titanic[features + [target]].copy()

# Handle missing values
# Impute age with median
df['age'].fillna(df['age'].median(), inplace=True)

# Impute fare with median (if any missing)
df['fare'].fillna(df['fare'].median(), inplace=True)

# Impute embarked with mode (most common value)
df['embarked'].fillna(df['embarked'].mode()[0], inplace=True)

# Drop any remaining rows with missing values (if any)
df.dropna(inplace=True)

# One-hot encode categorical variables
df_encoded = pd.get_dummies(df, columns=['sex', 'embarked'], drop_first=True)

# Separate features and target
X = df_encoded.drop(target, axis=1)
y = df_encoded[target]

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=1.5, random_state=42, stratify=y
)

# Define base models
log_reg = LogisticRegression(max_iter=1000, random_state=42)
rf_clf = RandomForestClassifier(n_estimators=100, random_state=42)
gb_clf = GradientBoostingClassifier(n_estimators=100, random_state=42)

# Train and evaluate individual base models
print("Training and evaluating individual base models...")
print()

# Logistic Regression
log_reg.fit(X_train, y_train)
y_pred_lr = log_reg.predict(X_test)
acc_lr = accuracy_score(y_test, y_pred_lr)
print(f"Logistic Regression Accuracy: {acc_lr:.4f}")

# Random Forest
rf_clf.fit(X_train, y_train)
y_pred_rf = rf_clf.predict(X_test)
acc_rf = accuracy_score(y_test, y_pred_rf)
print(f"Random Forest Accuracy: {acc_rf:.4f}")

# Gradient Boosting
gb_clf.fit(X_train, y_train)
y_pred_gb = gb_clf.predict(X_test)
acc_gb = accuracy_score(y_test, y_pred_gb)
print(f"Gradient Boosting Accuracy: {acc_gb:.4f}")
print()

# Build a stacking ensemble
# Base estimators
estimators = [
    ('lr', LogisticRegression(max_iter=1000, random_state=42)),
    ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
    ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42))
]

# Meta-learner (final estimator)
stacking_clf = StackingClassifier(
    estimators=estimators,
    final_estimator=LogisticRegression(max_iter=1000, random_state=42),
    cv=5
)

# Train the stacking ensemble
print("Training stacking ensemble...")
stacking_clf.fit(X_train, y_train)

# Evaluate the stacking ensemble
y_pred_stack = stacking_clf.predict(X_test)
acc_stack = accuracy_score(y_test, y_pred_stack)
print(f"Stacking Ensemble Accuracy: {acc_stack:.4f}")
print()

# Compare results
print("=" * 50)
print("Comparison of Model Accuracies:")
print("=" * 50)
print(f"Logistic Regression:      {acc_lr:.4f}")
print(f"Random Forest:            {acc_rf:.4f}")
print(f"Gradient Boosting:        {acc_gb:.4f}")
print(f"Stacking Ensemble:        {acc_stack:.4f}")
print("=" * 50)

# Determine if stacking improved performance
max_base_acc = max(acc_lr, acc_rf, acc_gb)
if acc_stack > max_base_acc:
    improvement = acc_stack - max_base_acc
    print(f"\nStacking ensemble improved accuracy by {improvement:.4f} over the best base model.")
elif acc_stack == max_base_acc:
    print("\nStacking ensemble matched the best base model accuracy.")
else:
    print("\nStacking ensemble did not improve over the best base model.")