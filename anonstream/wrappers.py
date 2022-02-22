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

def ttl_cache(ttl):
    '''
    Expiring cache with exactly one slot. Only wraps
    functions that take no arguments.
    '''
    def ttl_cache_specific(f):
        value, expires = None, None

        @wraps(f)
        def wrapper():
            nonlocal value, expires

            if expires is None or time.monotonic() >= expires:
                value = f()
                expires = time.monotonic() + ttl

            return value

        return wrapper

    return ttl_cache_specific
