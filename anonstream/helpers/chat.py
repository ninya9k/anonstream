# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from functools import lru_cache

import markupsafe
from quart import current_app, escape, url_for, Markup

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

@lru_cache
def get_emote_markup(emote_name, emote_file, emote_width, emote_height):
    emote_name_markup = escape(emote_name)
    width = '' if emote_width is None else f'width="{escape(emote_width)}" '
    height = '' if emote_height is None else f'height="{escape(emote_height)}" '
    return Markup(
        f'''<img class="emote" '''
        f'''src="{escape(url_for('static', filename=emote_file))}" '''
        f'''{width}{height}'''
        f'''alt="{emote_name_markup}" title="{emote_name_markup}">'''
    )

def insert_emotes(markup):
    assert isinstance(markup, markupsafe.Markup)
    for emote in EMOTES:
        emote_markup = get_emote_markup(
            emote['name'], emote['file'], emote['width'], emote['height'],
        )
        markup = emote['regex'].sub(emote_markup, markup)
    return Markup(markup)
