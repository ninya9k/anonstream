# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import time
from functools import wraps

def with_function_call(fn, *fn_args, **fn_kwargs):
    def with_result(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = fn(*fn_args, **fn_kwargs)
            return f(result, *args, **kwargs)
        return wrapper
    return with_result

def with_constant(x):
    return with_function_call(lambda: x)

def get_timestamp(monotonic=False, precise=False):
    n = 1_000_000_000
    if monotonic:
        timestamp = precise and time.monotonic() or time.monotonic_ns() // n
    else:
        timestamp = precise and time.time() or time.time_ns() // n
    return timestamp

def with_timestamp(monotonic=False, precise=False):
    def get_timestamp_specific():
        return get_timestamp(monotonic=monotonic, precise=precise)
    return with_function_call(get_timestamp_specific)

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

def ttl_cache_async(ttl):
    '''
    Async version of `ttl_cache`. Wraps zero-argument coroutines.
    '''
    def ttl_cache_specific(f):
        value, expires = None, None
        @wraps(f)
        async def wrapper():
            nonlocal value, expires
            if expires is None or time.monotonic() >= expires:
                value = await f()
                expires = time.monotonic() + ttl
            return value
        return wrapper
    return ttl_cache_specific
