import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras

# Set random seed for reproducibility
np.random.seed(42)

# Load Fashion MNIST dataset
(x_train, y_train), (x_test, y_test) = keras.datasets.fashion_mnist.load_data()

# Combine training and test labels to get full dataset distribution
y_all = np.concatenate([y_train, y_test])

# Class names for Fashion MNIST
class_names = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
               'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']

# Compute class frequencies
unique_classes, class_counts = np.unique(y_all, return_counts=True)
total_samples = len(y_all)

# Calculate class percentages
class_percentages = (class_counts / total_samples) * 100

# Log class distribution
print("Fashion MNIST Class Distribution:")
print("=" * 50)
for cls, count, percentage in zip(unique_classes, class_counts, class_percentages):
    print(f"Class {cls} ({class_names[cls]}): {count} samples ({percentage:.2f}%)")
print("=" * 50)
print(f"Total samples: {total_samples}")

# Verify that no class accounts for less than 8% of the dataset
min_percentage = np.min(class_percentages)
print(f"\nMinimum class percentage: {min_percentage:.2f}%")

if min_percentage >= 8.0:
    print("✓ All classes account for at least 8% of the dataset.")
else:
    print(f"✗ Warning: Some classes account for less than 8% of the dataset.")

# Assert that all classes meet the 8% threshold
assert min_percentage >= 8.0, f"Class balance check failed: minimum percentage is {min_percentage:.2f}%"

# Plot bar chart of class distribution
plt.figure(figsize=(12, 6))
plt.bar(unique_classes, class_percentages, color='steelblue', edgecolor='black')
plt.xlabel('Class', fontsize=12)
plt.ylabel('Percentage (%)', fontsize=12)
plt.title('Fashion MNIST Class Distribution', fontsize=14, fontweight='bold')
plt.xticks(unique_classes, [class_names[i] for i in unique_classes], rotation=45, ha='right')
plt.axhline(y=8.0, color='red', linestyle='--', linewidth=2, label='8% threshold')
plt.legend()
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.show()

print("\nClass balance check completed successfully!")
