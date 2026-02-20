
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import pandas as pd
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score
from catboost import CatBoostClassifier
import matplotlib.pyplot as plt

# Set random seed for reproducibility
np.random.seed(42)

# Fetch the adult dataset from OpenML
print("Fetching adult dataset...")
adult_data = fetch_openml('adult', version=2, as_frame=True, parser='auto')
X = adult_data.data
y = adult_data.target

# Identify categorical features
categorical_features = X.select_dtypes(include=['category', 'object']).columns.tolist()
print(f"Categorical features: {categorical_features}")

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training set size: {X_train.shape[0]}")
print(f"Test set size: {X_test.shape[0]}")

# Initialize CatBoostClassifier with basic parameters
# CatBoost handles categorical features natively
print("\nTraining initial CatBoost model...")
base_model = CatBoostClassifier(
    iterations=100,
    random_seed=42,
    verbose=0,
    cat_features=categorical_features
)

base_model.fit(X_train, y_train)
y_pred_base = base_model.predict(X_test)
base_accuracy = accuracy_score(y_test, y_pred_base)
print(f"Base model accuracy: {base_accuracy:.4f}")

# Hyperparameter tuning: depth and learning_rate
print("\nTuning hyperparameters (depth and learning_rate)...")
param_grid = {
    'depth': [4, 6, 8],
    'learning_rate': [0.01, 0.05, 0.1]
}

# Use a smaller subset for faster tuning in this example
tuning_model = CatBoostClassifier(
    iterations=50,
    random_seed=42,
    verbose=0,
    cat_features=categorical_features
)

grid_search = GridSearchCV(
    estimator=tuning_model,
    param_grid=param_grid,
    cv=3,
    scoring='accuracy',
    n_jobs=-1,
    verbose=0
)

gridsearch.fit(X_train, y_train)

print(f"Best parameters: {grid_search.best_params_}")
print(f"Best cross-validation accuracy: {grid_search.best_score_:.4f}")

# Train final model with best parameters
print("\nTraining final model with best parameters...")
final_model = CatBoostClassifier(
    iterations=100,
    depth=grid_search.best_params_['depth'],
    learning_rate=grid_search.best_params_['learning_rate'],
    random_seed=42,
    verbose=0,
    cat_features=categorical_features
)

final_model.fit(X_train, y_train)
y_pred_final = final_model.predict(X_test)
final_accuracy = accuracy_score(y_test, y_pred_final)
print(f"Final model accuracy: {final_accuracy:.4f}")

# Feature importance
print("\nExtracting feature importance...")
feature_importance = final_model.get_feature_importance()
feature_names = X.columns.tolist()

# Create a DataFrame for better visualization
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': feature_importance
}).sort_values('importance', ascending=False)

print("\nTop 10 most important features:")
print(importance_df.head(10))

# Visualize feature importance
plt.figure(figsize=(10, 6))
top_n = 10
top_features = importance_df.head(top_n)
plt.barh(range(top_n), top_features['importance'].values)
plt.yticks(range(top_n), top_features['feature'].values)
plt.xlabel('Feature Importance')
plt.ylabel('Feature')
plt.title('Top 10 Feature Importances (CatBoost)')
plt.gca().invert_yaxis()
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

print("\n=== Summary ===")
print(f"Base model accuracy: {base_accuracy:.4f}")
print(f"Tuned model accuracy: {final_accuracy:.4f}")
print(f"Best depth: {grid_search.best_params_['depth']}")
print(f"Best learning rate: {grid_search.best_params_['learning_rate']}")
print(f"Most important feature: {importance_df.iloc[0]['feature']}")