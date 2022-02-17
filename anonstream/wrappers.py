import time
from functools import wraps

def with_timestamp(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        timestamp = int(time.time())
        return f(timestamp, *args, **kwargs)

    return wrapper

def with_first_argument(x):
    def with_x(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(x, *args, **kwargs)

        return wrapper

    return with_x

def try_except_log(errors, exception_class):
    def try_except_log_specific(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exception_class as e:
                errors.append(e)

        return wrapper

    return try_except_log_specific
