import numpy as np
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, roc_auc_score

# Set random seed for reproducibility
np.random.seed(42)

# Load IMDB dataset from keras.datasets
# num_words limits vocabulary to the top 10000 most frequent words
num_words = 10000
(x_train_raw, y_train_raw), (x_test_raw, y_test_raw) = keras.datasets.imdb.load_data(num_words=num_words)

# Combine train and test for a unified split later
x_all = np.concatenate([x_train_raw, x_test_raw], axis=0)
y_all = np.concatenate([y_train_raw, y_test_raw], axis=0)

# Convert sequences to bag-of-words vectors
# Each review is a list of word indices; we create a count vector
def sequences_to_bow(sequences, num_words):
    """
    Convert sequences of word indices to bag-of-words count vectors.
    
    Args:
        sequences: list of lists, each inner list contains word indices
        num_words: vocabulary size
    
    Returns:
        numpy array of shape (num_samples, num_words) with word counts
    """
    bow_matrix = np.zeros((len(sequences), num_words), dtype=np.int32)
    for i, seq in enumerate(sequences):
        for word_idx in seq:
            if word_idx < num_words:
                bow_matrix[i, word_idx] += 1
    return bow_matrix

X_bow = sequences_to_bow(x_all, num_words)
y = y_all

# Split data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X_bow, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training samples: {X_train.shape[0]}")
print(f"Test samples: {X_test.shape[0]}")
print(f"Vocabulary size: {X_train.shape[1]}")

# Build and train Multinomial Naive Bayes classifier
model = MultinomialNB(alpha=1.0)
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

# Evaluate the model
accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print(f"\nModel Performance:")
print(f"Accuracy: {accuracy:.4f}")
print(f"ROC-AUC: {roc_auc:.4f}")

# Show the most indicative words for each class
# Get word index mapping
word_index = keras.datasets.imdb.get_word_index()
index_to_word = {idx: word for word, idx in word_index.items()}

# Get log probabilities for each class
# model.feature_log_prob_ has shape (n_classes, n_features)
# Higher log probability means more indicative of that class
log_prob_neg = model.feature_log_prob_[0]  # class 0 (negative)
log_prob_pos = model.feature_log_prob_[1]  # class 1 (positive)

# Compute log probability ratio: log(P(word|pos)) - log(P(word|neg))
log_ratio = log_prob_pos - log_prob_neg

# Get top words for positive sentiment (highest log ratio)
top_positive_indices = np.argsort(log_ratio)[-20:][::-1]
print("\nTop 20 words indicative of POSITIVE sentiment:")
for idx in top_positive_indices:
    word = index_to_word.get(idx, f"<UNK_{idx}>")
    print(f"  {word} (index {idx}, log_ratio: {log_ratio[idx]:.4f})")

# Get top words for negative sentiment (lowest log ratio)
top_negative_indices = np.argsort(log_ratio)[:20]
print("\nTop 20 words indicative of NEGATIVE sentiment:")
for idx in top_negative_indices:
    word = index_to_word.get(idx, f"<UNK_{idx}>")
    print(f"  {word} (index {idx}, log_ratio: {log_ratio[idx]:.4f})")

print("\nSentiment classification complete!")