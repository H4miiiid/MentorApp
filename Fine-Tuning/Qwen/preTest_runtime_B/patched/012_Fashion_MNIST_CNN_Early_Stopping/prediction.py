
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

def calculate_sum_of_squares(numbers):
    sum_of_squares = 0
    for num in numbers:
        sum_of_squares += num ** 2
    return sum_of_squares

def main():
    numbers = [1, 2, 3, 4, 5]
    result = calculate_sum_of_squares(numbers)
    print("The sum of squares is:", result)

if __name__ == "__main__":
    main()