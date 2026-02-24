
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import MobileNet
from tensorflow.keras.datasets import fashion_mnist
from tensorflow.keras.utils import to_categorical
import matplotlib.pyplot as plt

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# Load Fashion MNIST dataset
(x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()

# Use a subset of data for faster training
train_size = 10000
test_size = 2000
x_train = x_train[:train_size]
y_train = y_train[:train_size]
x_test = x_test[:test_size]
y_test = y_test[:test_size]

# Preprocess images for MobileNet
# MobileNet expects input shape (224, 224, 3)
def preprocess_images(images):
    # Resize from 28x28 to 224x224
    resized = tf.image.resize(images[..., np.newaxis], [224, 224])
    # Convert grayscale to RGB by repeating channels
    rgb = tf.repeat(resized, 3, axis=-1)
    # MobileNet preprocessing: scale to [-1, 1]
    preprocessed = tf.keras.applications.mobilenet.preprocess_input(rgb)
    return preprocessed.numpy()

print("Preprocessing training images...")
x_train_processed = preprocess_images(x_train)
print("Preprocessing test images...")
x_test_processed = preprocess_images(x_test)

# Convert labels to categorical
y_train_cat = to_categorical(y_train, 10)
y_test_cat = to_categorical(y_test, 10)

# Load pre-trained MobileNet without top layers
base_model = MobileNet(
    weights='imagenet',
    include_top=False,
    input_shape=(224, 224, 3),
    pooling='avg'
)

# Freeze base model layers initially
base_model.trainable = False

# Build the model with a dense classification head
model = keras.Sequential([
    base_model,
    layers.Dense(128, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(10, activation='softmax')
])

# Compile the model
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

print("\nModel architecture:")
model.summary()

# Train the model with frozen base (feature extraction)
print("\nTraining with frozen base model...")
history1 = model.fit(
    x_train_processed, y_train_cat,
    batch_size=32,
    epochs=3,
    validation_split=0.2,
    verbose=1
)

# Fine-tune: unfreeze the top layers of the base model
base_model.trainable = True

# Freeze all layers except the last few
for layer in base_model.layers[:-20]:
    layer.trainable = False

# Recompile with a lower learning rate for fine-tuning
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.0001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

print("\nFine-tuning top layers...")
history2 = model.fit(
    x_train_processed, y_train_cat,
    batch_size=32,
    epochs=3,
    validation_split=0.2,
    verbose=1
)

# Evaluate the model on test data
print("\nEvaluating model on test data...")
test_loss, test_accuracy = model.evaluate(x_test_processed, y_test_cat, verbose=0)
print(f"Test accuracy: {test_accuracy:.4f}")
print(f"Test loss: {test_loss:.4f}")

# Visualize training history
plt.figure(figsize=(12, 4))

# Combine histories
all_accuracy = history1.history['accuracy'] + history2.history['accuracy']
all_val_accuracy = history1.history['val_accuracy'] + history2.history['val_accuracy']
all_loss = history1.history['loss'] + history2.history['loss']
all_val_loss = history1.history['val_loss'] + history2.history['val_loss']

epochs_range = range(1, len(all_accuracy) + 1)

plt.subplot(1, 2, 1)
plt.plot(epochs_range, all_accuracy, label='Training Accuracy')
plt.plot(epochs_range, all_val_accuracy, label='Validation Accuracy')
plt.axvline(x=3, color='r', linestyle='--', label='Fine-tuning starts')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('Training and Validation Accuracy')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(epochs_range, all_loss, label='Training Loss')
plt.plot(epochs_range, all_val_loss, label='Validation Loss')
plt.axvline(x=3, color='r', linestyle='--', label='Fine-tuning starts')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Training and Validation Loss')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig('fashion_mnist_mobilenet_training.png', dpi=100, bbox_inches='tight')
print('[FAST_EVAL] plt.show() skipped')

# Make predictions on a few test samples
class_names = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
               'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']

predictions = model.predict(x_test_processed[:9])
predicted_classes = np.argmax(predictions, axis=1)

# Visualize predictions
plt.figure(figsize=(10, 10))
for i in range(9):
    plt.subplot(3, 3, i + 1)
    plt.imshow(x_test[i], cmap='gray')
    plt.title(f"Pred: {class_names[predicted_classes[i]]}\nTrue: {class_names[y_test[i]]}")
    plt.axis('off')
plt.tight_layout()
plt.savefig('fashion_mnist_predictions.png', dpi=100, bbox_inches='tight')
print('[FAST_EVAL] plt.show() skipped')

print("\nTransfer learning with MobileNet completed successfully!")
print(f"Final test accuracy: {test_accuracy:.4f}")