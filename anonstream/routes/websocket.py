# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from quart import current_app, websocket

from anonstream.user import see, ensure_allowedness, AllowednessException
from anonstream.websocket import websocket_outbound, websocket_inbound
from anonstream.routes.wrappers import with_user_from

@current_app.websocket('/live')
@with_user_from(websocket, fallback_to_token=True, ignore_allowedness=True)
async def live(timestamp, user_or_token):
    match user_or_token:
        case str() | None:
            await websocket.send_json({'type': 'kick'})
            await websocket.close(1001)
        case dict() as user:
            try:
                ensure_allowedness(user, timestamp=timestamp)
            except AllowednessException:
                await websocket.send_json({'type': 'kick'})
                await websocket.close(1001)
            else:
                queue = asyncio.Queue()
                user['websockets'][queue] = timestamp
                user['last']['reading'] = timestamp

                producer = websocket_outbound(queue, user)
                consumer = websocket_inbound(queue, user)
                try:
                    await asyncio.gather(producer, consumer)
                finally:
                    see(user)
                    user['websockets'].pop(queue)
