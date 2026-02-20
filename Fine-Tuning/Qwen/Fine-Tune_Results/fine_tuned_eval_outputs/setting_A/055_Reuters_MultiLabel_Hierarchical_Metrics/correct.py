import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import precision_score, recall_score, f1_score

# Set random seeds for reproducibility
np.random.seed(42)

# Load Reuters dataset
(x_train, y_train), (x_test, y_test) = keras.datasets.reuters.load_data(num_words=10000)

# Convert sequences to multi-hot encoded vectors
def vectorize_sequences(sequences, dimension=10000):
    results = np.zeros((len(sequences), dimension))
    for i, sequence in enumerate(sequences):
        results[i, sequence] = 1.0
    return results

x_train_vec = vectorize_sequences(x_train)
x_test_vec = vectorize_sequences(x_test)

# For multi-label, we need to convert single labels to multi-label format
# Reuters is originally single-label, but we'll treat it as multi-label
# by creating a binary matrix where each sample can have one or more labels
mlb = MultiLabelBinarizer()
y_train_multi = mlb.fit_transform([[label] for label in y_train])
y_test_multi = mlb.transform([[label] for label in y_test])

num_classes = y_train_multi.shape[1]

# Define a simple category hierarchy (parent-child relationships)
# For Reuters, we'll create a synthetic hierarchy for demonstration
# In a real scenario, this would be based on actual topic taxonomy
def create_synthetic_hierarchy(num_classes):
    """
    Create a synthetic hierarchy where:
    - Classes 0-9 are children of parent 0
    - Classes 10-19 are children of parent 1
    - etc.
    """
    hierarchy = {}
    num_parents = max(1, num_classes // 10)
    for i in range(num_classes):
        parent = i // 10
        if parent >= num_parents:
            parent = num_parents - 1
        hierarchy[i] = parent
    return hierarchy

hierarchy = create_synthetic_hierarchy(num_classes)

# Binary Relevance: train one classifier per label
class BinaryRelevance:
    def __init__(self, base_classifier):
        self.base_classifier = base_classifier
        self.classifiers = []
    
    def fit(self, X, y):
        """
        Train one binary classifier per label.
        X: feature matrix (n_samples, n_features)
        y: multi-label binary matrix (n_samples, n_labels)
        """
        n_labels = y.shape[1]
        self.classifiers = []
        for i in range(n_labels):
            clf = self.base_classifier.__class__(**self.base_classifier.get_params())
            # Only train if there are positive examples
            if np.sum(y[:, i]) > 0:
                clf.fit(X, y[:, i])
            else:
                # If no positive examples, create a dummy classifier that always predicts 0
                clf = None
            self.classifiers.append(clf)
        return self
    
    def predict(self, X):
        """
        Predict labels for X.
        Returns binary matrix (n_samples, n_labels)
        """
        predictions = []
        for clf in self.classifiers:
            if clf is not None:
                pred = clf.predict(X)
            else:
                pred = np.zeros(X.shape[0])
            predictions.append(pred)
        return np.column_stack(predictions)
    
    def predict_proba(self, X):
        """
        Predict probabilities for X.
        Returns probability matrix (n_samples, n_labels)
        """
        probas = []
        for clf in self.classifiers:
            if clf is not None and hasattr(clf, 'predict_proba'):
                proba = clf.predict_proba(X)[:, 1]
            else:
                proba = np.zeros(X.shape[0])
            probas.append(proba)
        return np.column_stack(probas)

# Train Binary Relevance model
base_clf = LogisticRegression(max_iter=100, random_state=42, solver='lbfgs')
br_model = BinaryRelevance(base_clf)
print("Training Binary Relevance model...")
br_model.fit(x_train_vec, y_train_multi)

# Predict on test set
y_pred = br_model.predict(x_test_vec)

# Compute hierarchical metrics
def compute_hierarchical_metrics(y_true, y_pred, hierarchy):
    """
    Compute hierarchical precision, recall, and F1.
    
    Hierarchical metrics consider the category hierarchy:
    - If a child category is predicted, the parent is implicitly predicted
    - Errors at higher levels in the hierarchy are penalized less
    """
    n_samples = y_true.shape[0]
    n_labels = y_true.shape[1]
    
    # Extend predictions and ground truth to include parent categories
    def extend_with_parents(y, hierarchy):
        y_extended = y.copy()
        for sample_idx in range(y.shape[0]):
            for label_idx in range(y.shape[1]):
                if y[sample_idx, label_idx] == 1:
                    # Add parent
                    parent = hierarchy.get(label_idx, -1)
                    if parent >= 0 and parent < n_labels:
                        y_extended[sample_idx, parent] = 1
        return y_extended
    
    y_true_extended = extend_with_parents(y_true, hierarchy)
    y_pred_extended = extend_with_parents(y_pred, hierarchy)
    
    # Compute metrics on extended labels
    # Use 'samples' average for multi-label
    precision = precision_score(y_true_extended, y_pred_extended, average='samples', zero_division=0)
    recall = recall_score(y_true_extended, y_pred_extended, average='samples', zero_division=0)
    f1 = f1_score(y_true_extended, y_pred_extended, average='samples', zero_division=0)
    
    return precision, recall, f1

# Compute standard and hierarchical metrics
standard_precision = precision_score(y_test_multi, y_pred, average='samples', zero_division=0)
standard_recall = recall_score(y_test_multi, y_pred, average='samples', zero_division=0)
standard_f1 = f1_score(y_test_multi, y_pred, average='samples', zero_division=0)

hier_precision, hier_recall, hier_f1 = compute_hierarchical_metrics(y_test_multi, y_pred, hierarchy)

print("\nStandard Metrics:")
print(f"Precision: {standard_precision:.4f}")
print(f"Recall: {standard_recall:.4f}")
print(f"F1-Score: {standard_f1:.4f}")

print("\nHierarchical Metrics:")
print(f"Precision: {hier_precision:.4f}")
print(f"Recall: {hier_recall:.4f}")
print(f"F1-Score: {hier_f1:.4f}")

# Compute metrics at different threshold levels
def compute_metrics_at_thresholds(y_true, y_proba, hierarchy, thresholds):
    """
    Compute hierarchical metrics at different probability thresholds.
    """
    precisions = []
    recalls = []
    f1s = []
    
    for threshold in thresholds:
        y_pred_thresh = (y_proba >= threshold).astype(int)
        p, r, f = compute_hierarchical_metrics(y_true, y_pred_thresh, hierarchy)
        precisions.append(p)
        recalls.append(r)
        f1s.append(f)
    
    return precisions, recalls, f1s

# Get probability predictions
y_proba = br_model.predict_proba(x_test_vec)

# Compute metrics at different thresholds
thresholds = np.linspace(0.1, 0.9, 20)
precisions, recalls, f1s = compute_metrics_at_thresholds(y_test_multi, y_proba, hierarchy, thresholds)

# Plot metric curves
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

axes[0].plot(thresholds, precisions, marker='o', color='blue', linewidth=2)
axes[0].set_xlabel('Threshold', fontsize=12)
axes[0].set_ylabel('Hierarchical Precision', fontsize=12)
axes[0].set_title('Precision vs Threshold', fontsize=14)
axes[0].grid(True, alpha=0.3)

axes[1].plot(thresholds, recalls, marker='s', color='green', linewidth=2)
axes[1].set_xlabel('Threshold', fontsize=12)
axes[1].set_ylabel('Hierarchical Recall', fontsize=12)
axes[1].set_title('Recall vs Threshold', fontsize=14)
axes[1].grid(True, alpha=0.3)

axes[2].plot(thresholds, f1s, marker='^', color='red', linewidth=2)
axes[2].set_xlabel('Threshold', fontsize=12)
axes[2].set_ylabel('Hierarchical F1-Score', fontsize=12)
axes[2].set_title('F1-Score vs Threshold', fontsize=14)
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('hierarchical_metrics_curves.png', dpi=100, bbox_inches='tight')
plt.show()

print("\nMetric curves plotted and saved as 'hierarchical_metrics_curves.png'")

# Plot Precision-Recall curve
fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(recalls, precisions, marker='o', linewidth=2, markersize=6)
ax.set_xlabel('Hierarchical Recall', fontsize=12)
ax.set_ylabel('Hierarchical Precision', fontsize=12)
ax.set_title('Hierarchical Precision-Recall Curve', fontsize=14)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('hierarchical_pr_curve.png', dpi=100, bbox_inches='tight')
plt.show()

print("Precision-Recall curve plotted and saved as 'hierarchical_pr_curve.png'")
print("\nProject completed successfully!")