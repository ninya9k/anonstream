import markupsafe
from functools import lru_cache

from quart import current_app, escape, url_for, Markup

EMOTES = current_app.emotes

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
