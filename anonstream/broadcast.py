from quart import current_app

from anonstream.utils.user import get_user_for_websocket

USERS = current_app.users
USERS_BY_TOKEN = current_app.users_by_token
USERS_UPDATE_BUFFER = current_app.users_update_buffer

def broadcast(users, payload):
    for user in users:
        for queue in user['websockets']:
            queue.put_nowait(payload)

def broadcast_users_update():
    users_for_websocket = {}
    for token in USERS_UPDATE_BUFFER:
        user = USERS_BY_TOKEN[token]
        token_hash = user['token_hash']
        users_for_websocket[token_hash] = get_user_for_websocket(user)

    if users_for_websocket:
        broadcast(
            users=USERS,
            payload={
                'type': 'set-users',
                'users': users_for_websocket,
            },
        )
        USERS_UPDATE_BUFFER.clear()
