import time

from quart import current_app

CONFIG = current_app.config
FAILURES = current_app.failures

def add_failure(message):
    timestamp = time.time_ns() // 1_000_000
    while timestamp in FAILURES:
        timestamp += 1
    FAILURES[timestamp] = message

    while len(FAILURES) > CONFIG['MAX_FAILURES']:
        FAILURES.popitem(last=False)

    return timestamp

def pop_failure(failure_id):
    try:
        return FAILURES.pop(failure_id)
    except KeyError:
        return None
