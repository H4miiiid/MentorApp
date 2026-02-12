import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.utils import to_categorical

# Set random seeds for reproducibility
np.random.seed(42)
import tensorflow as tf
tf.random.set_seed(42)

# Load the digits dataset from scikit-learn
digits = load_digits()
X = digits.data  # Shape: (n_samples, 64)
y = digits.target  # Shape: (n_samples,)

# Reshape images for CNN input (samples, height, width, channels)
# Original images are 8x8 grayscale
X = X.reshape(-1, 8, 8, 1)

# Normalize pixel values to [0, 1]
X = X.astype('float32') / 16.0  # Original values are 0-16

# Convert labels to one-hot encoding
y_categorical = to_categorical(y, num_classes=10)

# Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y_categorical, test_size=1.5, random_state=42, stratify=y
)

print(f"Training set size: {X_train.shape[0]}")
print(f"Test set size: {X_test.shape[0]}")
print(f"Image shape: {X_train.shape[1:]}")

# Build a CNN model with dropout layers
model = keras.Sequential([
    # First convolutional block
    layers.Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(8, 8, 1)),
    layers.MaxPooling2D(pool_size=(2, 2)),
    layers.Dropout(0.25),

    # Second convolutional block
    layers.Conv2D(64, kernel_size=(3, 3), activation='relu'),
    layers.Dropout(0.25),

    # Flatten and dense layers
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(10, activation='softmax')
])

# Compile the model
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Display model architecture
print("\nModel Architecture:")
model.summary()

# Train the model
print("\nTraining the model...")
history = model.fit(
    X_train, y_train,
    batch_size=32,
    epochs=10,
    validation_split=0.1,
    verbose=1
)

# Evaluate on test set
print("\nEvaluating on test set...")
test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
print(f"Test Loss: {test_loss:.4f}")
print(f"Test Accuracy: {test_accuracy:.4f} ({test_accuracy * 100:.2f}%)")

# Plot training history
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# Plot accuracy
axes[0].plot(history.history['accuracy'], label='Train Accuracy')
axes[0].plot(history.history['val_accuracy'], label='Validation Accuracy')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Accuracy')
axes[0].set_title('Model Accuracy over Epochs')
axes[0].legend()
axes[0].grid(True)

# Plot loss
axes[1].plot(history.history['loss'], label='Train Loss')
axes[1].plot(history.history['val_loss'], label='Validation Loss')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('Loss')
axes[1].set_title('Model Loss over Epochs')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
plt.savefig('training_history.png', dpi=100, bbox_inches='tight')
plt.show()

# Make predictions on a few test samples
print("\nSample Predictions:")
num_samples = 5
sample_indices = np.random.choice(len(X_test), num_samples, replace=False)
X_samples = X_test[sample_indices]
y_samples = y_test[sample_indices]

predictions = model.predict(X_samples, verbose=0)
predicted_classes = np.argmax(predictions, axis=1)
true_classes = np.argmax(y_samples, axis=1)

# Visualize sample predictions
fig, axes = plt.subplots(1, num_samples, figsize=(12, 3))
for i in range(num_samples):
    axes[i].imshow(X_samples[i].reshape(8, 8), cmap='gray')
    axes[i].set_title(f"True: {true_classes[i]}\nPred: {predicted_classes[i]}")
    axes[i].axis('off')

plt.tight_layout()
plt.savefig('sample_predictions.png', dpi=100, bbox_inches='tight')
plt.show()

print("\nDigits Classification with CNN and Dropout completed successfully!")
print(f"Final Test Accuracy: {test_accuracy * 100:.2f}%")