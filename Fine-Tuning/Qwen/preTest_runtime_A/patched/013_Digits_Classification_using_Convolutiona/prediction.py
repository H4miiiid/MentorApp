
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.models import Model

# Set random seeds for reproducibility
np.random.seed(42)
import tensorflow as tf
tf.random.set_seed(42)

# Load the digits dataset
digits = load_digits()
X = digits.data
y = digits.target

# Normalize pixel values to [0, 1]
X = X / 16.0

# Reshape for CNN input (samples, height, width, channels)
X_images = X.reshape(-1, 8, 8, 1)

# Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X_images, y, test_size=0.2, random_state=42
)

# ============================================
# Part 1: Build and train Convolutional Autoencoder
# ============================================

def build_convolutional_autoencoder(input_shape=(8, 8, 1), encoding_dim=16):
    """
    Build a convolutional autoencoder.

    Args:
        input_shape: Shape of input images
        encoding_dim: Dimension of the bottleneck layer

    Returns:
        autoencoder: Full autoencoder model
        encoder: Encoder part only
    """
    # Encoder
    input_img = layers.Input(shape=input_shape)
    x = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(input_img)
    x = layers.MaxPooling2D((2, 2), padding='same')(x)
    x = layers.Conv2D(8, (3, 3), activation='relu', padding='same')(x)
    x = layers.MaxPooling2D((2, 2), padding='same')(x)
    x = layers.Flatten()(x)
    encoded = layers.Dense(encoding_dim, activation='relu', name='bottleneck')(x)

    # Decoder
    x = layers.Dense(2 * 2 * 8, activation='relu')(encoded)
    x = layers.Reshape((2, 2, 8))(x)
    x = layers.Conv2D(8, (3, 3), activation='relu', padding='same')(x)
    x = layers.UpSampling2D((2, 2))(x)
    x = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(x)
    x = layers.UpSampling2D((2, 2))(x)
    decoded = layers.Conv2D(1, (3, 3), activation='sigmoid', padding='same')(x)

    # Full autoencoder
    autoencoder = Model(input_img, decoded)

    # Encoder model (for extracting features)
    encoder = Model(input_img, encoded)

    return autoencoder, encoder

# Build the autoencoder
autoencoder, encoder = build_convolutional_autoencoder(encoding_dim=16)

# Compile the autoencoder
autoencoder.compile(optimizer='adam', loss='mse')

print("Training Convolutional Autoencoder...")
# Train the autoencoder (reconstruction task)
history_ae = autoencoder.fit(
    X_train, X_train,
    epochs=10,
    batch_size=32,
    validation_data=(X_test, X_test),
    verbose=0
)

print(f"Autoencoder final loss: {history_ae.history['loss'][-1]:.4f}")

# ============================================
# Part 2: Extract bottleneck features and train Logistic Regression
# ============================================

# Extract encoded features from the bottleneck layer
X_train_encoded = encodr.predict(X_train, verbose=0)
X_test_encoded = encoder.predict(X_test, verbose=0)

print(f"\nBottleneck feature shape: {X_train_encoded.shape}")

# Train logistic regression on encoded features
print("Training Logistic Regression on bottleneck features...")
lr_classifier = LogisticRegression(max_iter=1000, random_state=42)
lr_classifier.fit(X_train_encoded, y_train)

# Evaluate logistic regression
y_pred_lr = lr_classifier.predict(X_test_encoded)
accuracy_lr = accuracy_score(y_test, y_pred_lr)
print(f"Logistic Regression Accuracy (on autoencoder features): {accuracy_lr:.4f}")

# ============================================
# Part 3: Build and train a direct CNN for comparison
# ============================================

def build_direct_cnn(input_shape=(8, 8, 1), num_classes=10):
    """
    Build a simple CNN classifier for direct comparison.

    Args:
        input_shape: Shape of input images
        num_classes: Number of output classes

    Returns:
        model: CNN classifier model
    """
    model = keras.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv2D(16, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(num_classes, activation='softmax')
    ])
    return model

# Build and compile the direct CNN
cnn_model = build_direct_cnn()
cnn_model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

print("\nTraining Direct CNN Classifier...")
# Train the CNN
history_cnn = cnn_model.fit(
    X_train, y_train,
    epochs=10,
    batch_size=32,
    validation_data=(X_test, y_test),
    verbose=0
)

# Evaluate the CNN
loss_cnn, accuracy_cnn = cnn_model.evaluate(X_test, y_test, verbose=0)
print(f"Direct CNN Accuracy: {accuracy_cnn:.4f}")

# ============================================
# Part 4: Visualization and Comparison
# ============================================

print("\n" + "="*50)
print("COMPARISON SUMMARY")
print("="*50)
print(f"Autoencoder + Logistic Regression Accuracy: {accuracy_lr:.4f}")
print(f"Direct CNN Accuracy: {accuracy_cnn:.4f}")
print("="*50)

# Visualize some reconstructions from the autoencoder
print("\nVisualizing autoencoder reconstructions...")
X_test_reconstructed = autoencoder.predict(X_test[:10], verbose=0)

fig, axes = plt.subplots(2, 10, figsize=(15, 3))
for i in range(10):
    # Original
    axes[0, i].imshow(X_test[i].reshape(8, 8), cmap='gray')
    axes[0, i].axis('off')
    if i == 0:
        axes[0, i].set_title('Original', fontsize=10)

    # Reconstructed
    axes[1, i].imshow(X_test_reconstructed[i].reshape(8, 8), cmap='gray')
    axes[1, i].axis('off')
    if i == 0:
        axes[1, i].set_title('Reconstructed', fontsize=10)

plt.tight_layout()
plt.savefig('autoencoder_reconstruction.png', dpi=100, bbox_inches='tight')
plt.close()

print("Reconstruction visualization saved as 'autoencoder_reconstruction.png'")
print("\nProject completed successfully!")