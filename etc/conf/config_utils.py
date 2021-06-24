

def toBool(value):
    """Convert any type of value to a boolean.

    The function uses the following heuristic:

    1. If the value can be converted to an integer, the integer is then
     converted to a boolean.
    2. If the value is a string, return True if it is equal to 'true'. False otherwise.
     Note that the comparison is case insensitive.
    3. If the value is neither an integer or a string, the bool() function is applied.

    >>> [toBool(x) for x in range(-2, 2)]
    [True, True, False, True]
    >>> [toBool(x) for x in ['-2', '-1', '0', '1', '2', 'Hello']]
    [True, True, False, True, True, False]
    >>> toBool(object())
    True
    >>> toBool(None)
    False
    """
    try:
        return bool(int(value))
    except (ValueError, TypeError):
        return value.lower() in ['true'] if isinstance(value, str) else bool(value)
