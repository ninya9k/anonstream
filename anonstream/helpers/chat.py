# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib

import markupsafe
from quart import current_app, escape, Markup

CONFIG = current_app.config
EMOTES = current_app.emotes

def generate_nonce_hash(nonce):
    parts = CONFIG['SECRET_KEY'] + b'nonce-hash\0' + nonce.encode()
    return hashlib.sha256(parts).hexdigest()

def get_scrollback(messages):
    n = CONFIG['MAX_CHAT_SCROLLBACK']
    if len(messages) < n:
        return messages
    return list(messages)[-n:]

def insert_emotes(markup):
    assert isinstance(markup, markupsafe.Markup)
    for name, regex, _position, _size in EMOTES:
        emote_markup = (
            f'<span class="emote" data-emote="{escape(name)}" '
            f'title="{escape(name)}">{escape(name)}</span>'
        )
        markup = regex.sub(emote_markup, markup)
    return Markup(markup)

def get_emotes_for_websocket():
    return {
        name: {
            'x': position[0],
            'y': position[1],
            'width': size[0],
            'height': size[1],
        }
        for name, _regex, position, size in EMOTES
    }
    return tuple(EMOTES.values())
