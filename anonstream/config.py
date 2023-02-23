# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import secrets

from werkzeug.security import generate_password_hash

from anonstream.utils.colour import color_to_colour
from anonstream.utils.user import generate_token

def update_flask_from_toml(toml_config, flask_config):
    auth_password = secrets.token_urlsafe(6)
    auth_pwhash = generate_password_hash(auth_password)

    flask_config.update({
        'SECRET_KEY_STRING': toml_config['secret_key'],
        'SECRET_KEY': toml_config['secret_key'].encode(),
        'AUTH_USERNAME': toml_config['auth']['username'],
        'AUTH_PWHASH': auth_pwhash,
        'AUTH_TOKEN': generate_token(),
        'ACCESS_CAPTCHA': toml_config['access']['captcha'],
     })
    for flask_section in toml_to_flask_sections(toml_config):
        flask_config.update(flask_section)

    return auth_password

def toml_to_flask_sections(config):
    TOML_TO_FLASK_SECTIONS = (
        toml_to_flask_section_socket,
        toml_to_flask_section_segments,
        toml_to_flask_section_title,
        toml_to_flask_section_names,
        toml_to_flask_section_memory,
        toml_to_flask_section_tasks,
        toml_to_flask_section_presence,
        toml_to_flask_section_chat,
        toml_to_flask_section_flood,
        toml_to_flask_section_captcha,
        toml_to_flask_section_nojs,
        toml_to_flask_section_emote,
    )
    for toml_to_flask_section in TOML_TO_FLASK_SECTIONS:
        yield toml_to_flask_section(config)

def toml_to_flask_section_socket(config):
    cfg = config['socket']
    return {
        'SOCKET_CONTROL_ENABLED': cfg['control']['enabled'],
        'SOCKET_CONTROL_ADDRESS': cfg['control']['address'],
        'SOCKET_EVENT_ENABLED': cfg['event']['enabled'],
        'SOCKET_EVENT_ADDRESS': cfg['event']['address'],
    }

def toml_to_flask_section_segments(config):
    cfg = config['segments']
    return {
        'SEGMENT_DIRECTORY': os.path.realpath(cfg['directory']),
        'SEGMENT_PLAYLIST': os.path.join(
            os.path.realpath(cfg['directory']),
            cfg['playlist'],
        ),
        'SEGMENT_PLAYLIST_CACHE_LIFETIME': cfg['playlist_cache_lifetime'],
        'SEGMENT_PLAYLIST_STALE_THRESHOLD': cfg['playlist_stale_threshold'],
        'SEGMENT_SEARCH_COOLDOWN': cfg['search_cooldown'],
        'SEGMENT_SEARCH_TIMEOUT': cfg['search_timeout'],
        'SEGMENT_STREAM_INITIAL_BUFFER': cfg['stream_initial_buffer'],
    }

def toml_to_flask_section_title(config):
    cfg = config['title']
    return {
        'STREAM_TITLE': cfg['file'],
        'STREAM_TITLE_CACHE_LIFETIME': cfg['file_cache_lifetime'],
    }

def toml_to_flask_section_names(config):
    cfg = config['names']
    return {
        'DEFAULT_HOST_NAME': cfg['broadcaster'],
        'DEFAULT_ANON_NAME': cfg['anonymous'],
    }

def toml_to_flask_section_memory(config):
    cfg = config['memory']
    assert cfg['states'] >= 0
    assert cfg['captchas'] >= 1
    assert cfg['failures'] >= 0
    assert cfg['chat_scrollback'] >= 0
    assert cfg['chat_messages'] >= cfg['chat_scrollback']
    return {
        'MAX_STATES': cfg['states'],
        'MAX_CAPTCHAS': cfg['captchas'],
        'MAX_FAILURES': cfg['failures'],
        'MAX_CHAT_MESSAGES': cfg['chat_messages'],
        'MAX_CHAT_SCROLLBACK': cfg['chat_scrollback'],
    }

def toml_to_flask_section_tasks(config):
    cfg = config['tasks']
    return {
        'TASK_ROTATE_EYES': cfg['rotate_eyes'],
        'TASK_ROTATE_USERS': cfg['rotate_users'],
        'TASK_ROTATE_CAPTCHAS': cfg['rotate_captchas'],
        'TASK_ROTATE_WEBSOCKETS': cfg['rotate_websockets'],
        'TASK_BROADCAST_PING': cfg['broadcast_ping'],
        'TASK_BROADCAST_USERS_UPDATE': cfg['broadcast_users_update'],
        'TASK_BROADCAST_STREAM_INFO_UPDATE': cfg['broadcast_stream_info_update'],
    }

def toml_to_flask_section_presence(config):
    cfg = config['presence']
    assert cfg['notwatching'] <= cfg['tentative'] <= cfg['absent']
    return {
        'PRESENCE_NOTWATCHING': cfg['notwatching'],
        'PRESENCE_TENTATIVE': cfg['tentative'],
        'PRESENCE_ABSENT': cfg['absent'],
    }

def toml_to_flask_section_chat(config):
    cfg = config['chat']
    assert cfg['force_captcha_every'] >= 0
    return {
        'CHAT_COMMENT_MAX_LENGTH': cfg['max_comment_length'],
        'CHAT_COMMENT_MAX_LINES': cfg['max_comment_lines'],
        'CHAT_NAME_MAX_LENGTH': cfg['max_name_length'],
        'CHAT_NAME_MIN_CONTRAST': cfg['min_name_contrast'],
        'CHAT_BACKGROUND_COLOUR': color_to_colour(cfg['background_color']),
        'CHAT_TRIPCODE_PASSWORD_MAX_LENGTH': cfg['max_tripcode_password_length'],
        'CHAT_LEGACY_TRIPCODE_ALGORITHM': cfg['legacy_tripcode_algorithm'],
        'CHAT_DEVERIFY_CLOCK': cfg['force_captcha_every'] or None,
    }

def toml_to_flask_section_flood(config):
    cfg = config['flood']
    assert cfg['video']['max_eyes'] >= 0
    return {
        'FLOOD_MESSAGE_DURATION': cfg['messages']['duration'],
        'FLOOD_MESSAGE_THRESHOLD': cfg['messages']['threshold'],
        'FLOOD_LINE_DURATION': cfg['lines']['duration'],
        'FLOOD_LINE_THRESHOLD': cfg['lines']['threshold'],
        'FLOOD_VIDEO_MAX_EYES': cfg['video']['max_eyes'],
        'FLOOD_VIDEO_COOLDOWN': cfg['video']['cooldown'],
        'FLOOD_VIDEO_EYES_EXPIRE_AFTER': cfg['video']['expire_after'],
        'FLOOD_VIDEO_OVERWRITE': cfg['video']['overwrite'],
    }

def toml_to_flask_section_captcha(config):
    cfg = config['captcha']
    return {
        'CAPTCHA_LIFETIME': cfg['lifetime'],
        'CAPTCHA_FONTS': cfg['fonts'],
        'CAPTCHA_ALPHABET': cfg['alphabet'],
        'CAPTCHA_LENGTH': cfg['length'],
        'CAPTCHA_BACKGROUND_COLOUR': color_to_colour(cfg['background_color']),
        'CAPTCHA_FOREGROUND_COLOUR': color_to_colour(cfg['foreground_color']),
    }

def toml_to_flask_section_nojs(config):
    cfg = config['nojs']
    return {
        'NOJS_REFRESH_MESSAGES': round(cfg['refresh_messages']),
        'NOJS_REFRESH_INFO': round(cfg['refresh_info']),
        'NOJS_REFRESH_USERS': round(cfg['refresh_users']),
        'NOJS_TIMEOUT_CHAT': round(cfg['timeout_chat']),
    }

def toml_to_flask_section_emote(config):
  cfg = config['emote']
  return {
    'EMOTE_SCHEMA': cfg['schema'],
  }
