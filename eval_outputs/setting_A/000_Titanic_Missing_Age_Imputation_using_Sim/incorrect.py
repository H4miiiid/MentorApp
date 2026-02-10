import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Set random seed for reproducibility
np.random.seed(42)

# Load the Titanic dataset from seaborn
titanic = sns.load_dataset('titanic')

# Display basic information about the dataset
print("Titanic Dataset Shape:", titanic.shape)
print("\nFirst few rows:")
print(titanic.head())
print("\nMissing values per column:")
print(titanic.isnull().sum())

# Select relevant features for modeling
# We'll use: pclass, sex, age, sibsp, parch, fare
# Target: survived
features = ['pclass', 'sex', 'age', 'sibsp', 'parch', 'fare']
target = 'survived'

# Create a copy of the dataset with selected features
df = titanic[features + [target]].copy()

# Convert categorical 'sex' to numeric (male=1, female=0)
df['sex'] = df['sex'].map({'male': 1, 'female': 0})

# Drop rows with missing target values
df = df.dropna(subset=[target])

print("\nDataset after selecting features and dropping missing targets:")
print("Shape:", df.shape)
print("Missing values:")
print(df.isnull().sum())

# Separate features and target
X = df[features]
y = df[target]

# Split data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("\n" + "="*60)
print("SCENARIO 1: Model WITHOUT Imputation (dropping missing ages)")
print("="*60)

# Drop rows with missing age values
X_train_no_impute = X_train.dropna()
y_train_no_impute = y_train.loc[X_train_no_impute.index]

X_test_no_impute = X_test.dropna()
y_test_no_impute = y_test.loc[X_test_no_impute.index]

print(f"Training set size after dropping missing ages: {X_train_no_impute.shape[0]}")
print(f"Test set size after dropping missing ages: {X_test_no_impute.shape[0]}")

# Train logistic regression model
model_no_impute = LogisticRegression(max_iter=1000, random_state=42)
model_no_impute.fit(X_train_no_impute, y_train_no_impute)

# Make predictions
y_pred_no_impute = model_no_impute.predict(X_test_no_impute)

# Calculate accuracy
accuracy_no_imput = accuracy_score(y_test_no_impute, y_pred_no_impute)
print(f"\nAccuracy WITHOUT imputation: {accuracy_no_impute:.4f}")

print("\n" + "="*60)
print("SCENARIO 2: Model WITH Imputation (median strategy)")
print("="*60)

# Create SimpleImputer with median strategy
imputer = SimpleImputer(strategy='median')

# Fit imputer on training data and transform both train and test
X_train_imputed = imputer.fit_transform(X_train)
X_test_imputed = imputer.transform(X_test)

# Convert back to DataFrame for clarity (optional)
X_train_imputed = pd.DataFrame(X_train_imputed, columns=features, index=X_train.index)
X_test_imputed = pd.DataFrame(X_test_imputed, columns=features, index=X_test.index)

print(f"Training set size with imputation: {X_train_imputed.shape[0]}")
print(f"Test set size with imputation: {X_test_imputed.shape[0]}")
print(f"\nMissing values after imputation (train): {X_train_imputed.isnull().sum().sum()}")
print(f"Missing values after imputation (test): {X_test_imputed.isnull().sum().sum()}")

# Train logistic regression model with imputed data
model_with_impute = LogisticRegression(max_iter=1000, random_state=42)
model_with_impute.fit(X_train_imputed, y_train)

# Make predictions
y_pred_with_impute = model_with_impute.predict(X_test_imputed)

# Calculate accuracy
accuracy_with_impute = accuracy_score(y_test, y_pred_with_impute)
print(f"\nAccuracy WITH imputation: {accuracy_with_impute:.4f}")

print("\n" + "="*60)
print("COMPARISON AND DISCUSSION")
print("="*60)

print(f"\nAccuracy WITHOUT imputation: {accuracy_no_impute:.4f}")
print(f"Accuracy WITH imputation: {accuracy_with_impute:.4f}")
print(f"Difference: {accuracy_with_impute - accuracy_no_impute:.4f}")

print("\nKey Observations:")
print("1. Data Retention:")
print(f"   - Without imputation: {X_train_no_impute.shape[0]} training samples")
print(f"   - With imputation: {X_train_imputed.shape[0]} training samples")
print(f"   - Retained {X_train_imputed.shape[0] - X_train_no_impute.shape[0]} additional samples")

print("\n2. Impact on Model Performance:")
if accuracy_with_impute > accuracy_no_impute:
    print("   - Imputation IMPROVED model accuracy")
    print("   - More training data helped the model generalize better")
elif accuracy_with_impute < accuracy_no_impute:
    print("   - Imputation DECREASED model accuracy slightly")
    print("   - However, we retained more data for training")
else:
    print("   - Imputation had NO significant impact on accuracy")

print("\n3. Benefits of Imputation:")
print("   - Preserves more data for training and testing")
print("   - Reduces bias from dropping missing values")
print("   - Median strategy is robust to outliers")
print("   - Allows model to make predictions on all test samples")

print("\n4. Median Imputation Details:")
print(f"   - Median age in training set: {X_train['age'].median():.2f}")
print(f"   - This value was used to fill missing ages")

print("\nConclusion:")
print("SimpleImputer with median strategy is a simple yet effective technique")
print("for handling missing values, especially for numerical features like age.")
print("It allows us to retain more data and often improves or maintains model")
print("performance compared to simply dropping missing values.")