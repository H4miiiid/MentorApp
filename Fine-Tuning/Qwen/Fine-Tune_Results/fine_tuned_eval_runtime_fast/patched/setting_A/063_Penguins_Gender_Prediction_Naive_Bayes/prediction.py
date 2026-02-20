
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, confusion_matrix, ConfusionMatrixDisplay

# Set random seed for reproducibility
np.random.seed(42)

# Load the penguins dataset from seaborn
penguins = sns.load_dataset('penguins')

# Display basic information about the dataset
print("Penguins dataset shape:", penguins.shape)
print("\nFirst few rows:")
print(penguins.head())
print("\nDataset info:")
print(penguins.info())
print("\nMissing values:")
print(penguins.isnull().sum())

# Drop rows with missing values
penguins_clean = penguins.dropna()
print("\nDataset shape after dropping missing values:", penguins_clean.shape)

# Create binary target for gender
# We'll use 'sex' column as the target (Male/Female)
print("\nGender distribution:")
print(penguins_clean['sex'].value_counts())

# Prepare features and target
# Features: species, island, bill_length_mm, bill_depth_mm, flipper_length_mm, body_mass_g
# Target: sex (gender)

# Select features
feature_cols = ['species', 'island', 'bill_length_mm', 'bill_depth_mm', 
                'flipper_length_mm', 'body_mass_g']
X = penguins_clean[feature_cols].copy()
y = penguins_clean['sex'].copy()

# Encode categorical features (species and island)
le_species = LabelEncoder()
le_island = LabelEncoder()

X['species'] = le_species.fit_transform(X['species'])
X['island'] = le_island.fit_transform(X['island'])

print("\nFeatures after encoding:")
print(X.head())

# Encode target variable (sex)
le_sex = LabelEncoder()
y_encoded = le_sex.fit_transform(y)

print("\nTarget encoding:")
for i, label in enumerate(le_sex.classes_):
    print(f"{label}: {i}")

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

print("\nTraining set size:", X_train.shape[0])
print("Testing set size:", X_test.shape[0])

# Train Gaussian Naive Bayes classifier
gnb = GaussianNB()
gnb.fit(X_train, y_train)

print("\nGaussian Naive Bayes model trained successfully.")

# Make predictions on test set
y_pred = gnb.predict(X_test)

# Evaluate the model
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average='binary')

print("\n=== Model Evaluation ===")
print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")

# Compute and display confusion matrix
cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(cm)

# Visualize confusion matrix
fig, ax = plt.subplots(figsize=(8, 6))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=le_sex.classes_)
disp.plot(ax=ax, cmap='Blues', values_format='d')
plt.title('Confusion Matrix for Penguin Gender Prediction')
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Analyze feature correlations to discuss Naive Bayes assumptions
print("\n=== Feature Correlation Analysis ===")
correlation_matrix = X.corr()
print("\nCorrelation matrix:")
print(correlation_matrix)

# Visualize correlation heatmap
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm', 
            center=0, square=True, linewidths=1, ax=ax)
plt.title('Feature Correlation Heatmap')
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Discussion on why Naive Bayes may struggle with correlated features
print("\n=== Discussion: Naive Bayes and Correlated Features ===")
print("""
Naive Bayes assumes that all features are conditionally independent given the class label.
This is the 'naive' assumption that gives the algorithm its name.

From the correlation matrix above, we can observe:
1. Strong correlations exist between some features (e.g., flipper_length_mm and body_mass_g).
2. Bill measurements may also show correlations with body size features.

Why Naive Bayes may struggle with correlated features:
- The independence assumption is violated when features are correlated.
- Correlated features provide redundant information, which Naive Bayes counts multiple times.
- This can lead to overconfident probability estimates and potentially biased predictions.
- The model may give too much weight to correlated feature groups.

Despite this limitation, Naive Bayes often performs surprisingly well in practice,
especially for text classification and when the independence assumption is approximately met.
In this penguin gender prediction task, the model still achieves reasonable accuracy
because the correlations, while present, may not be strong enough to severely degrade performance.
""")

# Additional analysis: show which features have strong correlations
print("\nStrongly correlated feature pairs (|correlation| > 0.5):")
for i in range(len(correlation_matrix.columns)):
    for j in range(i+1, len(correlation_matrix.columns)):
        if abs(correlation_matrix.iloc[i, j]) > 0.5:
            print(f"{correlation_matrix.columns[i]} <-> {correlation_matrix.columns[j]}: "
                  f"{correlation_matrix.iloc[i, j]:.3f}")

print("\n=== Analysis Complete ===")