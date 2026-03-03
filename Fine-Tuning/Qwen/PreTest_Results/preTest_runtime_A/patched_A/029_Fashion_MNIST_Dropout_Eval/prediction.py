
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.datasets import fashion_mnist

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# Load Fashion MNIST dataset
(x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()

# Normalize pixel values to [0, 1]
x_train = x_train.astype('float32') / 255.0
x_test = x_test.astype('float32') / 255.0

# Reshape data to add channel dimension (28, 28, 1)
x_train = np.expand_dims(x_train, axis=-1)
x_test = np.expand_dims(x_test, axis=-1)

# Convert labels to categorical (one-hot encoding)
y_train_cat = keras.utils.to_categorical(y_train, 10)
y_test_cat = keras.utils.to_categorical(y_test, 10)

# Split training data into train and validation sets
val_split = 0.2
val_size = int(len(x_train) * val_split)
x_val = x_train[:val_size]
y_val = y_train_cat[:val_size]
x_train_sub = x_train[val_size:]
y_train_sub = y_train_cat[val_size:]

print(f"Training samples: {len(x_train_sub)}")
print(f"Validation samples: {len(x_val)}")
print(f"Test samples: {len(x_test)}")

# Define CNN without dropout
def create_cnn_without_dropout():
    model = keras.Sequential([
        layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
        layers.MaxPooling2D((2, 2)),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dense(10, activation='softmax')
    ])
    return model

# Define CNN with dropout
def create_cnn_with_dropout():
    model = keras.Sequential([
        layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(10, activation='softmax')
    ])
    return model

# Create and compile model without dropout
print("\n=== Training CNN without Dropout ===")
model_no_dropout = create_cnn_without_dropout()
model_no_dropout.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Train model without dropout
history_no_dropout = model_no_dropout.fit(
    x_train_sub, y_train_sub,
    epochs=5,
    batch_size=128,
    validation_data=(x_val, y_val),
    verbose=0
)

# Get final training and validation accuracy for model without dropout
train_acc_no_dropout = history_no_dropout.history['accuracy'][-1]
val_acc_no_dropout = history_no_dropout.history['val_accuracy'][-1]
gap_no_dropout = train_acc_no_dropout - val_acc_no_dropout

print(f"Final Training Accuracy (No Dropout): {train_acc_no_dropout:.4f}")
print(f"Final Validation Accuracy (No Dropout): {val_acc_no_dropout:.4f}")
print(f"Gap (No Dropout): {gap_no_dropout:.4f}")

# Create and compile model with dropout
print("\n=== Training CNN with Dropout ===")
model_with_dropout = create_cnn_with_dropout()
model_with_dropout.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Train model with dropout
history_with_dropout = model_with_dropout.fit(
    x_train_sub, y_train_sub,
    epochs=5,
    batch_size=128,
    validation_data=(x_val, y_val),
    verbose=0
)

# Get final training and validation accuracy for model with dropout
train_acc_with_dropout = history_with_dropout.history['accuracy'][-1]
val_acc_with_dropout = history_with_dropout.history['val_accuracy'][-1]
gap_with_dropout = train_acc_with_dropout - val_acc_with_dropout

print(f"Final Training Accuracy (With Dropout): {train_acc_with_dropout:.4f}")
print(f"Final Validation Accuracy (With Dropout): {val_acc_with_dropout:.4f}")
print(f"Gap (With Dropout): {gap_with_dropout:.4f}")

# Compare the gaps
print("\n=== Comparison ===")
print(f"Gap without dropout: {gap_no_dropout:.4f}")
print(f"Gap with dropout: {gap_with_dropout:.4f}")
print(f"Difference in gaps: {gap_no_dropout - gap_with_dropout:.4f}")

# Verify that dropout reduces overfitting (smaller gap)
if gap_with_dropout < gap_no_dropout:
    print("\n✓ Dropout successfully reduced overfitting (smaller gap between training and validation accuracy)")
else:
    print("\n✗ Dropout did not reduce the gap in this run (may need more epochs or different hyperparameters)")

# Record the gap values
results = {
    'gap_no_dropout': gap_no_dropout,
    'gap_with_dropout': gap_with_dropout,
    'train_acc_no_dropout': train_acc_no_dropout,
    'val_acc_no_dropout': val_acc_no_dropout,
    'train_acc_with_dropout': train_acc_with_dropout,
    'val_acc_with_dropout': val_acc_with_dropout
}

print("\n=== Recorded Results ===")
for key, value in results.items():
    print(f"{key}: {value:.4f}")