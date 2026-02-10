import numpy as np

from sklearn.datasets import load_diabetes
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt

# Set random seeds for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# Load the diabetes dataset
diabetes = load_diabetes()
X = diabetes.data
y = diabetes.target

# Split the data into training and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Normalize the input features using StandardScaler
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Function to create a neural network model with configurable hidden layer sizes
def create_model(hidden_layers):
    """
    Create a feed-forward neural network for regression.

    Parameters:
    -----------
    hidden_layers : list of int
        List containing the number of neurons in each hidden layer.

    Returns:
    --------
    model : keras.Model
        Compiled Keras model.
    """
    model = keras.Sequential()

    # Input layer
    model.add(layers.Input(shape=(X_train_scaled.shape[1],)))

    # Hidden layers
    for units in hidden_layers:
        model.add(layers.Dense(units, activation='relu'))

    # Output layer (single neuron for regression)
    model.add(layers.Dense(1))

    # Compile the model
    model.compile(
        optimizer='adam',
        loss='mse',
        metrics=['mae']
    )

    return model

# Experiment with different hidden layer configurations
configurations = [
    [64],
    [64, 32],
    [128, 64, 32]
]

results = []

print("Experimenting with different neural network architectures:\n")

for i, config in enumerate(configurations):
    print(f"Configuration {i+1}: Hidden layers = {config}")

    # Create the model
    model = create_model(config)

    # Train the model
    history = model.fit(
        X_train_scaled, y_train,
        epochs=100,
        batch_size=32,
        validation_split=0.2,
        verbose=0,
        random_state=42
    )

    # Make predictions on the test set
    y_pred = model.predict(X_test_scaled, verbose=0).flatten()

    # Calculate RMSE
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    # Store results
    results.append({
        'config': config,
        'rmse': rmse,
        'history': history,
        'model': model
    })

    print(f"  Test RMSE: {rmse:.2f}\n")

# Select the best model based on RMSE
best_result = min(results, key=lambda x: x['rmse'])
best_config = best_result['config']
best_rmse = best_result['rmse']
best_model = best_result['model']

print(f"Best configuration: {best_config}")
print(f"Best Test RMSE: {best_rmse:.2f}")

# Visualize training history for the best model
plt.figure(figsize=(12, 4))

plt.subplot(1, 2, 1)
plt.plot(best_result['history'].history['loss'], label='Training Loss')
plt.plot(best_result['history'].history['val_loss'], label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss (MSE)')
plt.title('Training and Validation Loss')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(best_result['history'].history['mae'], label='Training MAE')
plt.plot(best_result['history'].history['val_mae'], label='Validation MAE')
plt.xlabel('Epoch')
plt.ylabel('MAE')
plt.title('Training and Validation MAE')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

# Visualize predictions vs actual values
y_pred_best = best_model.predict(X_test_scaled, verbose=0).flatten()

plt.figure(figsize=(8, 6))
plt.scatter(y_test, y_pred_best, alpha=0.6, edgecolors='k')
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
plt.xlabel('Actual Disease Progression')
plt.ylabel('Predicted Disease Progression')
plt.title(f'Predictions vs Actual (RMSE: {best_rmse:.2f})')
plt.grid(True)
plt.tight_layout()
plt.show()

print("\nModel training and evaluation complete.")