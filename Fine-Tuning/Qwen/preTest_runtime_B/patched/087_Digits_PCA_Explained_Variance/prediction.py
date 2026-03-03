
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
from sklearn.decomposition import PCA
from sklearn.datasets import load_digits

# Load the digits dataset
digits = load_digits()
X = digits.data

# Perform PCA
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

# Calculate explained variance
explained_variance = pca.explained_variance_ratio_

# Print the explained variance
print(explained_variance)