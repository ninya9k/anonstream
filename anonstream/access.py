# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

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
