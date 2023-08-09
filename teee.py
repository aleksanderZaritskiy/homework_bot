import sys
import traceback


def func(x, y):
    try:
        x / y
    except (ZeroDivisionError, TypeError) as error:
        print(dir(error))
        print(', '.join(str(error.add_note).split(' ')))


print(func('f', 0))
