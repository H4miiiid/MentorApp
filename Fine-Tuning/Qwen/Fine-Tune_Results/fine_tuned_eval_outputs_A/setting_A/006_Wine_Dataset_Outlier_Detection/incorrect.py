import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_wine
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Set random seed for reproducibility
np.random.seed(42)

# Load the wine dataset
wine = load_wine()
X = wine.data
y = wine.target

print("Wine dataset loaded.")
print(f"Number of samples: {X.shape[0]}")
print(f"Number of features: {X.shape[1]}")
print()

# Standardize the features for better performance
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Fit an IsolationForest model to detect outliers
# contamination parameter controls the proportion of outliers expected
isolation_forest = IsolationForest(contamination=1.5, random_state=42)
predictions = isolation_forest.fit_predict(X_scaled)

# IsolationForest returns 1 for inliers and -1 for outliers
outliers = predictions == -1
inliers = predictions == 1

num_outliers = np.sum(outliers)
num_inliers = np.sum(inliers)

print(f"Number of outliers detected: {num_outliers}")
print(f"Number of inliers: {num_inliers}")
print(f"Percentage of outliers: {100 * num_outliers / len(predictions):.2f}%")
print()

# Apply PCA to reduce to 2 dimensions for visualization
pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X_scaled)

print(f"Explained variance by first two principal components: {pca.explained_variance_ratio_.sum():.2f}")
print()

# Visualize the results
plt.figure(figsize=(10, 6))

# Plot inliers
plt.scatter(X_pca[inliers, 0], X_pca[inliers, 1], 
            c='blue', label='Inliers', alpha=0.6, edgecolors='k', s=50)

# Plot outliers
plt.scatter(X_pca[outliers, 0], X_pca[outliers, 1], 
            c='red', label='Outliers', alpha=0.8, edgecolors='k', s=100, marker='X')

plt.xlabel('First Principal Component')
plt.ylabel('Second Principal Component')
plt.title('Wine Dataset: Outlier Detection using Isolation Forest')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Discussion
print("Discussion:")
print(f"The Isolation Forest algorithm flagged {num_outliers} out of {len(predictions)} samples as outliers.")
print(f"This represents approximately {100 * num_outliers / len(predictions):.1f}% of the dataset.")
print("These outliers are samples that have unusual feature combinations compared to the majority.")
print("In the PCA visualization, outliers (red X markers) tend to be located in sparser regions,")
print("away from the dense clusters of normal samples (blue circles).")
print("The contamination parameter was set to 0.1, meaning we expected about 10% outliers.")