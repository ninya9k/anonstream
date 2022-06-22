import time

from quart import current_app

FAILURES = current_app.failures

def add_failure(message):
    timestamp = time.time_ns() // 1_000_000
    while timestamp in FAILURES:
        timestamp += 1
    FAILURES[timestamp] = message
    return timestamp

def pop_failure(failure_id):
    try:
        return FAILURES.pop(failure_id)
    except KeyError:
        return None
