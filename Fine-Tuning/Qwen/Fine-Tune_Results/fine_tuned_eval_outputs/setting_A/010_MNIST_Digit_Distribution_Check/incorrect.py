import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras

# Set random seed for reproducibility
np.random.seed(42)

# Load MNIST dataset
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

# Combine training and test labels to get the full dataset distribution
y_all = np.concatenate([y_train, y_test])

# Count the number of samples per digit (0-9)
digits = np.arange(10)
digit_counts = np.array([np.sum(y_all == digit) for digit in digits])

# Calculate total number of samples
total_samples = len(y_all)

# Calculate percentage for each digit
digit_percentages = (digit_counts / total_samples) * 100

# Print distribution information
print("MNIST Digit Distribution:")
print("=" * 40)
for digit in digits:
    count = digit_counts[digit]
    percentage = digit_percentages[digit]
    print(f"Digit {digit}: {count:5d} samples ({percentage:5.2f}%)")
print("=" * 40)
print(f"Total samples: {total_samples}")

# Plot histogram of digit distribution
plt.figure(figsize=(10, 6))
plt.bar(digits, digit_counts, color='steelblue', edgecolor='black', alpha=0.7)
plt.xlabel('Digit', fontsize=12)
plt.ylabel('Number of Samples', fontsize=12)
plt.title('MNIST Digit Distribution', fontsize=14, fontweight='bold')
plt.xticks(digits)
plt.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on top of bars
for i, (digit, count) in enumerate(zip(digits, digit_counts)):
    plt.text(digit, count + 100, str(count), ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.show(

# Assert that each class contains at least 5% of the total samples
min_percentage = 5.0
for digit in digits:
    percentage = digit_percentages[digit]
    assert percentage >= min_percentage, f"Digit {digit} has only {percentage:.2f}% of samples, which is less than {min_percentage}%"

print(f"\nAssertion passed: All digits have at least {min_percentage}% of the total samples.")