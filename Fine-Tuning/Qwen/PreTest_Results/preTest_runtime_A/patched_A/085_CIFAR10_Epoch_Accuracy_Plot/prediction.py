
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.datasets import cifar10

# Load CIFAR-10 dataset
(x_train, y_train), (x_test, y_test) = cifar10.load_data()



if FAST_EVAL:
    try:
        x_train = x_train[:512]; y_train = y_train[:512]
        x_test  = x_test[:128]; y_test  = y_test[:128]
    except Exception:
        pass

# Normalize pixel values to [0, 1]
x_train = x_train.astype('float32') / 255.0
x_test = x_test.astype('float32') / 255.0

# Convert labels to categorical (one-hot encoding)
y_train = keras.utils.to_categorical(y_train, 10)
y_test = keras.utils.to_categorical(y_test, 10)

# Build a simple CNN model
model = keras.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 3)),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.Flatten(),
    layers.Dense(64, activation='relu'),
    layers.Dense(10, activation='softmax')
])

# Compile the model
model.compile(optimizer='adam',
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# Train the model for 20 epochs and record test accuracy after each epoch
epochs = 5
test_accuracies = []

for epoch in range(epochs):
    # Train for one epoch
    model.fit(x_train, y_train, epochs=5, batch_size=64, verbose=0)
    
    # Evaluate on test set
    test_loss, test_acc = model.evaluate(x_test, y_test, verbose=0)
    test_accuracies.append(test_acc)
    
    print(f"Epoch {epoch + 1}/{epochs} - Test Accuracy: {test_acc:.4f}")

# Plot the accuracy curve
plt.figure(figsize=(10, 6))
plt.plot(range(1, epochs + 1), test_accuracies, marker='o', linestyle='-', linewidth=2)
plt.xlabel('Epoch', fontsize=12)
plt.ylabel('Test Accuracy', fontsize=12)
plt.title('CIFAR-10 Test Accuracy over Epochs', fontsize=14)
plt.grid(True, alpha=0.3)
plt.tight_layout()
print('[FAST_EVAL] plt.show() skipped')

# Check if accuracy is monotonically increasing
is_monotonic = all(test_accuracies[i] <= test_accuracies[i + 1] for i in range(len(test_accuracies) - 1))

if is_monotonic:
    print("\nThe test accuracy is monotonically increasing.")
else:
    print("\nThe test accuracy is NOT monotonically increasing.")
    print("Note: In practice, test accuracy may fluctuate due to the stochastic nature of training.")

print(f"\nFinal test accuracy: {test_accuracies[-1]:.4f}")