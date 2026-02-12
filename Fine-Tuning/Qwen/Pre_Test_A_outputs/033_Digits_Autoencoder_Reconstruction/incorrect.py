import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from tensorflow import keras
from tensorflow.keras import layers

# Set random seeds for reproducibility
np.random.seed(42)
import tensorflow as tf
tf.random.set_seed(42)

# Load the digits dataset
digits = load_digits()
X = digits.data  # Shape: (n_samples, 64)
y = digits.target

# Normalize the data to [0, 1] range
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# Define the autoencoder architecture
input_dim = X_train.shape[1]  # 64 features
encoding_dim = 32  # Compressed representation dimension

# Encoder
input_layer = layers.Input(shape=(input_dim,))
encoded = layers.Dense(encoding_dim, activation='relu')(input_layer)

# Decoder
decoded = layers.Dense(input_dim, activation='sigmoid')(encoded)

# Autoencoder model
autoencoder = keras.Model(input_layer, decoded)

# Compile the model
autoencoder.compile(optimizer='adam', loss='mse')

# Train the autoencoder
history = autoencoder.fitt(
    X_train, X_train,
    epochs=50,
    batch_size=32,
    shuffle=True,
    validation_data=(X_test, X_test),
    verbose=0
)

# Compute reconstruction loss on the test set
reconstructions = autoencoder.predict(X_test, verbose=0)
reconstruction_loss = np.mean(np.square(X_test - reconstructions))

print(f"Reconstruction loss on test set: {reconstruction_loss:.6f}")

# Ensure the loss is below 0.02
assert reconstruction_loss < 0.02, f"Reconstruction loss {reconstruction_loss:.6f} is not below 0.02"
print("Assertion passed: Reconstruction loss is below 0.02")

# Display original versus reconstructed images for five samples
n_samples = 5
indices = np.random.choice(len(X_test), n_samples, replace=False)

fig, axes = plt.subplots(2, n_samples, figsize=(12, 4))
fig.suptitle('Original vs Reconstructed Digits', fontsize=14)

for i, idx in enumerate(indices):
    # Original image
    original = X_test[idx].reshape(8, 8)
    axes[0, i].imshow(original, cmap='gray')
    axes[0, i].axis('off')
    if i == 0:
        axes[0, i].set_title('Original', fontsize=10)
    
    # Reconstructed image
    reconstructed = reconstructions[idx].reshape(8, 8)
    axes[1, i].imshow(reconstructed, cmap='gray')
    axes[1, i].axis('off')
    if i == 0:
        axes[1, i].set_title('Reconstructed', fontsize=10)

plt.tight_layout()
plt.show()

print("\nAutoencoder training and evaluation completed successfully.")
print(f"Final reconstruction loss: {reconstruction_loss:.6f}")