# math_utils.py

def add(a, b):
    return a + b

def divide(x, y):
    if y == 0:
        raise ValueError("Division by zero")
    return x / y
