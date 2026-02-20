import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.datasets import fashion_mnist
import keras_tuner as kt

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# Load and preprocess Fashion MNIST dataset
(x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()

# Normalize pixel values to [0, 1]
x_train = x_train.astype('float32') / 255.0
x_test = x_test.astype('float32') / 255.0

# Reshape to add channel dimension (28, 28, 1)
x_train = np.expand_dims(x_train, axis=-1)
x_test = np.expand_dims(x_test, axis=-1)

print(f"Training data shape: {x_train.shape}")
print(f"Test data shape: {x_test.shape}")
print(f"Number of classes: {len(np.unique(y_train))}")

# Define the model-building function for hyperparameter tuning
def build_model(hp):
    """
    Build a CNN model with hyperparameters to tune.

    Hyperparameters to explore:
    - Number of filters in Conv2D layers
    - Kernel size
    - Dropout rate
    """
    model = keras.Sequential()

    # First convolutional block
    hp_filters_1 = hp.Int('filters_1', min_value=32, max_value=128, step=32)
    hp_kernel_size = hp.Choice('kernel_size', values=[3, 5])

    model.add(layers.Conv2D(
        filters=hp_filters_1,
        kernel_size=hp_kernel_size,
        activation='relu',
        input_shape=(28, 28, 1)
    ))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))

    # Second convolutional block
    hp_filters_2 = hp.Int('filters_2', min_value=64, max_value=256, step=64)
    model.add(layers.Conv2D(
        filters=hp_filters_2,
        kernel_size=hp_kernel_size,
        activation='relu'
    ))
    model.add(layers.MaxPooling2D(pool_size=(2, 2)))

    # Flatten and dense layers
    model.add(layers.Flatten())

    # Dropout layer with tunable rate
    hp_dropout = hp.Float('dropout', min_value=0.2, max_value=0.5, step=0.1)
    model.add(layers.Dropout(hp_dropout))

    model.add(layers.Dense(128, activation='relu'))
    model.add(layers.Dropout(hp_dropout))
    model.add(layers.Dense(10, activation='softmax'))

    # Compile the model
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )

    return model

# Initialize the hyperparameter tuner (RandomSearch)
tuner = kt.RandomSearch(
    build_model,
    objective='val_accuracy',
    max_trials=10,  # Number of different configurations to try
    executions_per_trial=1,  # Number of times to train each configuration
    directory='fashion_mnist_tuning',
    project_name='cnn_hyperparameter_search',
    seed=42
)

print("\n=== Hyperparameter Search Space ===")
print("filters_1: [32, 64, 96, 128]")
print("filters_2: [64, 128, 192, 256]")
print("kernel_size: [3, 5]")
print("dropout: [0.2, 0.3, 0.4, 0.5]")
print(f"Total trials: {tuner.max_trials}")

# Perform hyperparameter search
print("\n=== Starting Hyperparameter Search ===")
tuner.search(
    x_train, y_train,
    epochs=5,  # Keep epochs low for reasonable runtime
    validation_split=0.2,
    verbose=0
)

print("\n=== Hyperparameter Search Complete ===")

# Get the best hyperparameters
best_hps = tuner.get_best_hyperparameters(num_trials=1)[0]

print("\n=== Best Hyperparameters ===")
print(f"filters_1: {best_hps.get('filters_1')}")
print(f"filters_2: {best_hps.get('filters_2')}")
print(f"kernel_size: {best_hps.get('kernel_size')}")
print(f"dropout: {best_hps.get('dropout')}")

# Build and train the best model on full training data
print("\n=== Training Best Model ===")
best_model = tuner.hypermodel.build(best_hps)

history = best_model.fit(
    x_train, y_train,
    epochs=5,
    validation_split=0.2,
    verbose=0
)

# Evaluate on test set
test_loss, test_accuracy = best_model.evaluate(x_test, y_test, verbose=0)
print(f"\n=== Best Model Test Accuracy: {test_accuracy:.4f} ===")

# Visualize the search space results
print("\n=== Visualizing Search Space ===")

# Get all trials
all_trials = tuner.oracle.get_best_trials(num_trials=tuner.max_trials)

# Extract hyperparameters and validation accuracies
filters_1_list = []
filters_2_list = []
kernel_size_list = []
dropout_list = []
val_acc_list = []

for trial in all_trials:
    hp_values = trial.hyperparameters.values
    filters_1_list.append(hp_values['filters_1'])
    filters_2_list.append(hp_values['filters_2'])
    kernel_size_list.append(hp_values['kernel_size'])
    dropout_list.append(hp_values['dropout'])
    # Get the best validation accuracy for this trial
    val_acc = trial.score if trial.score is not None else 0
    val_acc_list.append(val_acc)

# Create visualizations
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
fig.suptitle('Hyperparameter Search Space Exploration', fontsize=16)

# Plot 1: filters_1 vs validation accuracy
axes[0, 0].scatter(filters_1_list, val_acc_list, c=val_acc_list, cmap='viridis', s=100, alpha=0.7)
axes[0, 0].set_xlabel('Number of Filters (Layer 1)')
axes[0, 0].set_ylabel('Validation Accuracy')
axes[0, 0].set_title('Filters (Layer 1) vs Validation Accuracy')
axes[0, 0].grid(True, alpha=0.3)

# Plot 2: filters_2 vs validation accuracy
axes[0, 1].scatter(filters_2_list, val_acc_list, c=val_acc_list, cmap='viridis', s=100, alpha=0.7)
axes[0, 1].set_xlabel('Number of Filters (Layer 2)')
axes[0, 1].set_ylabel('Validation Accuracy')
axes[0, 1].set_title('Filters (Layer 2) vs Validation Accuracy')
axes[0, 1].grid(True, alpha=0.3)

# Plot 3: kernel_size vs validation accuracy
axes[1, 0].scatter(kernel_size_list, val_acc_list, c=val_acc_list, cmap='viridis', s=100, alpha=0.7)
axes[1, 0].set_xlabel('Kernel Size')
axes[1, 0].set_ylabel('Validation Accuracy')
axes[1, 0].set_title('Kernel Size vs Validation Accuracy')
axes[1, 0].set_xticks([3, 5])
axes[1, 0].grid(True, alpha=0.3)

# Plot 4: dropout vs validation accuracy
scatter = axes[1, 1].scatter(dropout_list, val_acc_list, c=val_acc_list, cmap='viridis', s=100, alpha=0.7)
axes[1, 1].set_xlabel('Dropout Rate')
axes[1, 1].set_ylabel('Validation Accuracy')
axes[1, 1].set_title('Dropout Rate vs Validation Accuracy')
axes[1, 1].grid(True, alpha=0.3)

# Add colorbar
plt.colorbar(scatter, ax=axes[1, 1], label='Validation Accuracy')

plt.tight_layout()
plt.savefig('hyperparameter_search_visualization.png', dpi=100, bbox_inches='tight')
print("Visualization saved as 'hyperparameter_search_visualization.png'")
plt.show()

# Discussion of trade-offs
print("\n=== Trade-offs Discussion ===")
print("""
Key Trade-offs in Hyperparameter Search:

1. Number of Filters:
   - More filters increase model capacity and ability to learn complex features
   - Trade-off: Higher computational cost and risk of overfitting
   - Observation: Moderate filter counts often provide good balance

2. Kernel Size:
   - Larger kernels (5x5) capture broader spatial patterns
   - Smaller kernels (3x3) capture fine-grained details with fewer parameters
   - Trade-off: 3x3 kernels are more parameter-efficient; 5x5 may help with larger patterns

3. Dropout Rate:
   - Higher dropout (0.4-0.5) provides stronger regularization
   - Lower dropout (0.2-0.3) allows more information flow
   - Trade-off: Too high can underfit; too low may overfit
   - Observation: Moderate dropout (0.3-0.4) often works well

4. Search Strategy:
   - RandomSearch explores diverse configurations efficiently
   - Trade-off: May miss optimal configuration vs exhaustive grid search
   - Benefit: Much faster than grid search for large search spaces

5. Training Time:
   - More trials and epochs improve chances of finding best config
   - Trade-off: Computational cost increases linearly
   - Current setup: 10 trials × 5 epochs balances exploration and runtime
""")

print("\n=== Summary ===")
print(f"Best configuration achieved {test_accuracy:.4f} test accuracy")
print(f"Total trials evaluated: {len(all_trials)}")
print("Hyperparameter tuning helps identify optimal model configurations")
print("while balancing performance, computational cost, and generalization.")