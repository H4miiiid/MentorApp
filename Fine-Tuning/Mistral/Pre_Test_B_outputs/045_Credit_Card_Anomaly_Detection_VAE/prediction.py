import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, classification_report
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# ========================================
# 1. Generate Synthetic Credit Card Dataset
# ========================================
# Create a dataset with normal and anomalous transactions
# We'll use make_classification to generate features and labels
# where label 0 = normal, label 1 = anomaly
X, y = make_classification(
    n_samples=10000,
    n_features=20,
    n_informative=15,
    n_redundant=5,
    n_classes=2,
    weights=[0.95, 0.05],  # 95% normal, 5% anomalies
    flip_y=0.01,
    random_state=42
)

# Convert to DataFrame for easier handling
feature_names = [f'feature_{i}' for i in range(X.shape[1])]
df = pd.DataFrame(X, columns=feature_names)
df['label'] = y  # 0 = normal, 1 = anomaly

print(f"Dataset shape: {df.shape}")
print(f"Normal transactions: {(df['label'] == 0).sum()}")
print(f"Anomalous transactions: {(df['label'] == 1).sum()}")

# ========================================
# 2. Prepare Data for VAE Training
# ========================================
# For anomaly detection with VAE, we train only on normal transactions
# and use reconstruction error to detect anomalies

# Separate normal and anomalous data
normal_data = df[df['label'] == 0].drop('label', axis=1).values
anomalous_data = df[df['label'] == 1].drop('label', axis=1).values

# Split normal data into train and validation
X_train, X_val = train_test_split(normal_data, test_size=0.2, random_state=42)

# Standardize the data
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
anomalous_scaled = scaler.transform(anomalous_data)

print(f"\nTraining set shape: {X_train_scaled.shape}")
print(f"Validation set shape: {X_val_scaled.shape}")
print(f"Anomalous set shape: {anomalous_scaled.shape}")

# ========================================
# 3. Build Variational Autoencoder (VAE)
# ========================================

class Sampling(layers.Layer):
    """Uses (z_mean, z_log_var) to sample z, the vector encoding a transaction."""
    def call(self, inputs):
        z_mean, z_log_var = inputs
        batch = tf.shape(z_mean)[0]
        dim = tf.shape(z_mean)[1]
        epsilon = tf.keras.backend.random_normal(shape=(batch, dim), seed=42)
        return z_mean + tf.exp(0.5 * z_log_var) * epsilon

# Encoder
input_dim = X_train_scaled.shape[1]
latent_dim = 8

encoder_inputs = keras.Input(shape=(input_dim,))
x = layers.Dense(16, activation='relu')(encoder_inputs)
x = layers.Dense(12, activation='relu')(x)
z_mean = layers.Dense(latent_dim, name='z_mean')(x)
z_log_var = layers.Dense(latent_dim, name='z_log_var')(x)
z = Sampling()([z_mean, z_log_var])
encoder = keras.Model(encoder_inputs, [z_mean, z_log_var, z], name='encoder')

# Decoder
latent_inputs = keras.Input(shape=(latent_dim,))
x = layers.Dense(12, activation='relu')(latent_inputs)
x = layers.Dense(16, activation='relu')(x)
decoder_outputs = layers.Dense(input_dim, activation='linear')(x)
decoder = keras.Model(latent_inputs, decoder_outputs, name='decoder')

# VAE Model
class VAE(keras.Model):
    def __init__(self, encoder, decoder, **kwargs):
        super(VAE, self).__init__(**kwargs)
        self.encoder = encoder
        self.decoder = decoder
        self.total_loss_tracker = keras.metrics.Mean(name='total_loss')
        self.reconstruction_loss_tracker = keras.metrics.Mean(name='reconstruction_loss')
        self.kl_loss_tracker = keras.metrics.Mean(name='kl_loss')

    @property
    def metrics(self):
        return [
            self.total_loss_tracker,
            self.reconstruction_loss_tracker,
            self.kl_loss_tracker,
        ]

    def train_step(self, data):
        with tf.GradientTape() as tape:
            z_mean, z_log_var, z = self.encoder(data, training=True)
            reconstruction = self.decoder(z, training=True)
            reconstruction_loss = tf.reduce_mean(
                tf.reduce_sum(
                    keras.losses.mean_squared_error(data, reconstruction), axis=-1
                )
            )
            kl_loss = -0.5 * tf.reduce_mean(
                tf.reduce_sum(1 + z_log_var - tf.square(z_mean) - tf.exp(z_log_var), axis=-1)
            )
            total_loss = reconstruction_loss + kl_loss
        grads = tape.gradient(total_loss, self.trainable_weights)
        self.optimizer.apply_gradients(zip(grads, self.trainable_weights))
        self.total_loss_tracker.update_state(total_loss)
        self.reconstruction_loss_tracker.update_state(reconstruction_loss)
        self.kl_loss_tracker.update_state(kl_loss)
        return {
            'loss': self.total_loss_tracker.result(),
            'reconstruction_loss': self.reconstruction_loss_tracker.result(),
            'kl_loss': self.kl_loss_tracker.result(),
        }

    def call(self, inputs):
        z_mean, z_log_var, z = self.encoder(inputs)
        reconstruction = self.decoder(z)
        return reconstruction

vae = VAE(encoder, decoder)
vae.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001))

# ========================================
# 4. Train the VAE
# ========================================
print("\nTraining VAE...")
history = vae.fit(
    X_train_scaled,
    epochs=10,
    batch_size=128,
    verbose=0
)

print("Training complete.")

# ========================================
# 5. Compute Reconstruction Error
# ========================================
def compute_reconstruction_error(model, data):
    """Compute reconstruction error for each sample."""
    reconstructions = model(data)
    mse = np.mean(np.square(data - reconstructions), axis=1)
    return mse

# Compute reconstruction errors
train_errors = compute_reconstruction_error(vae, X_train_scaled)
val_errors = compute_reconstruction_error(vae, X_val_scaled)
anomalous_errors = compute_reconstruction_error(vae, anomalous_scaled)

print(f"\nMean reconstruction error (train): {np.mean(train_errors):.4f}")
print(f"Mean reconstruction error (validation): {np.mean(val_errors):.4f}")
print(f"Mean reconstruction error (anomalies): {np.mean(anomalous_errors):.4f}")

# ========================================
# 6. Set Threshold and Detect Anomalies
# ========================================
# Use a percentile of the validation errors as threshold
threshold = np.percentile(val_errors, 95)
print(f"\nAnomaly detection threshold (95th percentile): {threshold:.4f}")

# Create test set combining validation (normal) and anomalous data
X_test = np.vstack([X_val_scaled, anomalous_scaled])
y_test = np.hstack([np.zeros(len(X_val_scaled)), np.ones(len(anomalous_scaled))])

# Compute reconstruction errors on test set
test_errors = compute_reconstruction_error(vae, X_test)

# Predict anomalies based on threshold
y_pred = (test_errors > threshold).astype(int)

# ========================================
# 7. Evaluate Detection Performance
# ========================================
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)

print(f"\n{'='*50}")
print("Anomaly Detection Results")
print(f"{'='*50}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Normal', 'Anomaly']))

# ========================================
# 8. Visualization
# ========================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot 1: Training history
axes[0].plot(history.history['loss'], label='Total Loss')
axes[0].plot(history.history['reconstruction_loss'], label='Reconstruction Loss')
axes[0].plot(history.history['kl_loss'], label='KL Loss')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Loss')
axes[0].set_title('VAE Training History')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Plot 2: Reconstruction error distribution
axes[1].hist(val_errors, bins=50, alpha=0.6, label='Normal (Validation)', color='blue')
axes[1].hist(anomalous_errors, bins=50, alpha=0.6, label='Anomalies', color='red')
axes[1].axvline(threshold, color='green', linestyle='--', linewidth=2, label=f'Threshold ({threshold:.4f})')
axes[1].set_xlabel('Reconstruction Error')
axes[1].set_ylabel('Frequency')
axes[1].set_title('Reconstruction Error Distribution')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('vae_anomaly_detection.png', dpi=100, bbox_inches='tight')
print("\nVisualization saved as 'vae_anomaly_detection.png'")
plt.show()

print("\nCredit Card Anomaly Detection VAE - Complete!")