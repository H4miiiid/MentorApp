import numpy as np
from tensorflow import keras
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, confusion_matrix
import matplotlib.pyplot as plt

# Set random seed for reproducibility
np.random.seed(42)

# Load IMDB dataset from keras.datasets
# num_words=10000 means we only keep the top 10,000 most frequent words
num_words = 10000
(x_train, y_train), (x_test, y_test) = keras.datasets.imdb.load_data(num_words=num_words)

print(f"Training samples: {len(x_train)}")
print(f"Test samples: {len(x_test)}")
print(f"Example review (word indices): {x_train[0][:20]}...")  # First 20 word indices
print(f"Example label: {y_train[0]}")

# Convert reviews to bag-of-words vectors
# Each review is a list of word indices; we convert to a binary/count vector
def reviews_to_bow(reviews, num_words):
    """
    Convert list of reviews (each review is a list of word indices)
    to bag-of-words matrix.
    
    Args:
        reviews: list of lists, each inner list contains word indices
        num_words: vocabulary size
    
    Returns:
        numpy array of shape (num_reviews, num_words) with word counts
    """
    bow_matrix = np.zeros((len(reviews), num_words), dtype=np.int32)
    for i, review in enumerate(reviews):
        for word_idx in review:
            if word_idx < num_words:
                bow_matrix[i, word_idx] += 1
    return bow_matrix

# Convert training and test data to bag-of-words
print("\nConverting reviews to bag-of-words vectors...")
X_train_bow = reviews_to_bow(x_train, num_words)
X_test_bow = reviews_to_bow(x_test, num_words)

print(f"Training BOW shape: {X_train_bow.shape}")
print(f"Test BOW shape: {X_test_bow.shape}")

# Train Multinomial Naive Bayes classifier
print("\nTraining Multinomial Naive Bayes classifier...")
clf = MultinomialNB(alpha=1.0)  # alpha is the smoothing parameter
clf.fit(X_train_bow, y_train)

# Make predictions
y_train_pred = clf.predict(X_train_bow)
y_test_pred = clf.predict(X_test_bow)

# Calculate accuracy
train_accuracy = accuracy_score(y_train, y_train_pred)
test_accuracy = accuracy_score(y_test, y_test_pred)

print(f"\nTraining Accuracy: {train_accuracy:.4f}")
print(f"Test Accuracy: {test_accuracy:.4f}")

# Compute confusion matrix
cm = confusion_matrix(y_test, y_test_pred)
print("\nConfusion Matrix (Test Set):")
print(cm)
print("\nConfusion Matrix Interpretation:")
print(f"True Negatives (TN): {cm[0, 0]}")
print(f"False Positives (FP): {cm[0, 1]}")
print(f"False Negatives (FN): {cm[1, 0]}")
print(f"True Positives (TP): {cm[1, 1]}")

# Visualize confusion matrix
plt.figure(figsize=(8, 6))
plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
plt.title('Confusion Matrix - IMDB Sentiment Analysis')
plt.colorbar()
tick_marks = np.arange(2)
plt.xticks(tick_marks, ['Negative', 'Positive'])
plt.yticks(tick_marks, ['Negative', 'Positive'])

# Add text annotations
thresh = cm.max() / 2.0
for i in range(2):
    for j in range(2):
        plt.text(j, i, format(cm[i, j], 'd'),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black")

plt.ylabel('True Label')
plt.xlabel('Predicted Label')
plt.tight_layout()
plt.show(

print("\nModel training and evaluation complete!")