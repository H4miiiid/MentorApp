
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_iris
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans

# Set random seed for reproducibility
np.random.seed(42)

# Load the iris dataset
iris = load_iris()
X = iris.data
y = iris.target
target_names = iris.target_names

# Apply t-SNE to reduce dimensions to 2
tsne = TSNE(n_components=2, random_state=42, perplexity=30, max_iter=1000)
X_tsne = tsne.fit_transform(X)

# Perform K-Means clustering to find centroids (k=3 for 3 species)
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
kmeans.fit(X_tsne)
centroids = kmeans.cluster_centers_

# Create visualization
plt.figure(figsize=(10, 8))

# Plot the t-SNE reduced data points colored by true species
colors = ['red', 'green', 'blue']
for i, target_name in enumerate(target_names):
    indices = y == i
    plt.scatter(X_tsne[indices, 0], X_tsne[indices, 1], 
                c=colors[i], label=target_name, alpha=0.6, s=50)

# Overlay cluster centroids
plt.scatter(centroids[:, 0], centroids[:, 1], 
            c='black', marker='X', s=200, edgecolors='yellow', 
            linewidths=2, label='Centroids')

plt.xlabel('t-SNE Component 1', fontsize=12)
plt.ylabel('t-SNE Component 2', fontsize=12)
plt.title('Iris Dataset: t-SNE Visualization with Cluster Centroids', fontsize=14)
plt.legend(loc='best')
plt.grid(True, alpha=0.3)
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Discussion of separation quality
print("=" * 60)
print("Separation Quality Analysis")
print("=" * 60)
print("\nThe t-SNE visualization reveals the following:")
print("\n1. Cluster Separation:")
print("   - Setosa (red) forms a well-separated, compact cluster")
print("   - Versicolor (green) and Virginica (blue) show some overlap")
print("   - This reflects the known similarity between versicolor and virginica")

print("\n2. Centroid Positions:")
print("   - Black 'X' markers indicate K-Means cluster centroids")
print("   - Centroids are positioned at the center of mass of each cluster")
print("   - The centroid for setosa is clearly separated from the others")

print("\n3. t-SNE Characteristics:")
print("   - t-SNE preserves local structure and reveals natural groupings")
print("   - The 2D projection captures the main variance in the data")
print("   - Distances between clusters in t-SNE space may not reflect")
print("     actual distances in the original 4D feature space")

print("\n4. Overall Quality:")
print("   - Good separation for setosa (easily distinguishable)")
print("   - Moderate separation for versicolor and virginica")
print("   - The visualization effectively shows the three-class structure")
print("=" * 60)