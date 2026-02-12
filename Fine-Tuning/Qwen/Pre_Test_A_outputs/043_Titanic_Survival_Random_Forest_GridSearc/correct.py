import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder

# Set random seed for reproducibility
np.random.seed(42)

# Generate synthetic Titanic-like dataset
# Features: Pclass, Sex, Age, SibSp, Parch, Fare
# Target: Survived (0 or 1)
n_samples = 891

# Create synthetic data with realistic distributions
data = {
    'Pclass': np.random.choice([1, 2, 3], size=n_samples, p=[0.24, 0.21, 0.55]),
    'Sex': np.random.choice(['male', 'female'], size=n_samples, p=[0.65, 0.35]),
    'Age': np.random.normal(29.7, 14.5, n_samples).clip(0.42, 80),
    'SibSp': np.random.choice([0, 1, 2, 3, 4, 5], size=n_samples, p=[0.68, 0.23, 0.05, 0.02, 0.01, 0.01]),
    'Parch': np.random.choice([0, 1, 2, 3, 4, 5, 6], size=n_samples, p=[0.76, 0.13, 0.08, 0.01, 0.01, 0.005, 0.005]),
    'Fare': np.random.lognormal(3.0, 1.2, n_samples).clip(0, 512)
}

df = pd.DataFrame(data)

# Generate target variable with some correlation to features
# Higher survival for females, higher class, younger age
survival_prob = np.zeros(n_samples)
for i in range(n_samples):
    prob = 0.3  # base probability
    if df.loc[i, 'Sex'] == 'female':
        prob += 0.4
    if df.loc[i, 'Pclass'] == 1:
        prob += 0.2
    elif df.loc[i, 'Pclass'] == 2:
        prob += 0.1
    if df.loc[i, 'Age'] < 16:
        prob += 0.15
    survival_prob[i] = min(prob, 0.95)

df['Survived'] = (np.random.random(n_samples) < survival_prob).astype(int)

# Introduce some missing values in Age (similar to real Titanic dataset)
missing_age_indices = np.random.choice(n_samples, size=int(0.2 * n_samples), replace=False)
df.loc[missing_age_indices, 'Age'] = np.nan

print("Titanic Dataset (Synthetic)")
print(df.head())
print(f"\nDataset shape: {df.shape}")
print(f"\nMissing values:\n{df.isnull().sum()}")
print(f"\nSurvival distribution:\n{df['Survived'].value_counts()}")

# Preprocessing
# Handle missing values in Age by filling with median
df['Age'].fillna(df['Age'].median(), inplace=True)

# Encode categorical variable 'Sex'
le = LabelEncoder()
df['Sex'] = le.fit_transform(df['Sex'])

# Separate features and target
X = df.drop('Survived', axis=1)
y = df['Survived']

print("\nPreprocessed features:")
print(X.head())

# Split data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\nTraining set size: {X_train.shape[0]}")
print(f"Test set size: {X_test.shape[0]}")

# Define the parameter grid for GridSearchCV
param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10]
}

print("\nParameter grid for GridSearchCV:")
print(param_grid)

# Create Random Forest classifier
rf = RandomForestClassifier(random_state=42)

# Perform GridSearchCV
print("\nPerforming GridSearchCV...")
grid_search = GridSearchCV(
    estimator=rf,
    param_grid=param_grid,
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    verbose=1
)

grid_search.fit(X_train, y_train)

print("\nGridSearchCV completed.")
print(f"Best parameters: {grid_search.best_params_}")
print(f"Best cross-validation accuracy: {grid_search.best_score_:.4f}")

# Get the best model
best_model = grid_search.best_estimator_

# Evaluate on test set
y_pred = best_model.predict(X_test)
test_accuracy = accuracy_score(y_test, y_pred)

print(f"\nTest set accuracy: {test_accuracy:.4f}")

# Display classification report
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Not Survived', 'Survived']))

# Display confusion matrix
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': best_model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nFeature Importance:")
print(feature_importance)

print("\n=== Titanic Survival Random Forest GridSearch Complete ===")
print(f"Best model parameters: {grid_search.best_params_}")
print(f"Test accuracy: {test_accuracy:.4f}")
