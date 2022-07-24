# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json

from quart import current_app

def start_event_server_at(address):
    return asyncio.start_unix_server(serve_event_client, address)

async def serve_event_client(reader, writer):
    reader.feed_eof()
    queue = asyncio.Queue()
    current_app.event_queues.add(queue)
    try:
        while True:
            event = await queue.get()
            event_json = json.dumps(event, separators=(',', ':'))
            writer.write(event_json.encode())
            writer.write(b'\n')
            try:
                await writer.drain()
            # Because we used reader.feed_eof(), if the client sends anything
            # an AsserionError will be raised
            except (ConnectionError, AssertionError):
                break
    finally:
        current_app.event_queues.remove(queue)

def notify_event_sockets(event):
    for queue in current_app.event_queues:
        queue.put_nowait(event)
