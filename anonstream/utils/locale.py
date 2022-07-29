import types

SPEC = {
    'anonstream': {
        'error': {
            'invalid_token': str,
            'captcha': str,
            'captcha_again': str,
            'impostor': str,
            'broadcaster_should_log_in': str,
            'wrong_username_or_password': str,
            'blacklisted': str,
            'not_whitelisted': str,
            'offline': str,
            'ratelimit': str,
            'limit': str,
        },
        'internal': {
            'captcha_required': str,
            'captcha_incorrect': str,
            'captcha_expired': str,
            'message_ratelimited': str,
            'message_suspected_duplicate': str,
            'message_empty': str,
            'message_practically_empty': str,
            'message_too_long': str,
            'message_too_many_lines': str,
            'message_too_many_apparent_lines': str,
            'appearance_changed': str,
            'name_empty': str,
            'name_too_long': str,
            'colour_invalid_css': str,
            'colour_insufficient_contrast': str,
            'password_too_long': str,
        },
        'captcha': {
            'captcha_failed_to_load': str,
            'click_for_a_new_captcha': str,
        },
        'home': {
            'info': str,
            'chat': str,
            'both': str,
            'source': str,
            'users': str,
            'users_in_chat': str,
            'stream_chat': str,
        },
        'stream': {
            'offline': str,
        },
        'info': {
            'viewers': str,
            'uptime': str,
            'reload_stream': str,
        },
        'chat': {
            'users': str,
            'click_to_refresh': str,
            'hide_timeout_notice': str,
            'watching': str,
            'not_watching': str,
            'you': str,
            'timed_out': str,
        },
        'form': {
            'click_to_dismiss': str,
            'send_a_message': str,
            'captcha': str,
            'settings': str,
            'captcha_failed_to_load': str,
            'click_for_a_new_captcha': str,
            'chat': str,
            'name': str,
            'tripcode': str,
            'no_tripcode': str,
            'set': str,
            'cleared': str,
            'undo': str,
            'tripcode_password': str,
            'return_to_chat': str,
            'update': str,
        },
        'js': {
            'offline': str,
            'reload_stream': str,
            'chat_scroll_paused': str,
            'not_connected': str,
            'broadcaster': str,
            'loading': str,
            'click_for_a_new_captcha': str,
            'viewers': str,
            'you': str,
            'watching': str,
            'not_watching': str,
            'errors': str,
            'connecting_to_chat': str,
            'connected_to_chat': str,
            'disconnected_from_chat': str,
            'error_connecting_to_chat': str,
            'error_connecting_to_chat_terse': str,
        }
    },
    'http': {
        '400': str | None,
        '401': str | None,
        '403': str | None,
        '404': str | None,
        '405': str | None,
        '410': str | None,
        '500': str | None,
    }
}

class Nonconforming(Exception):
    pass

def _conform_to_spec(data, spec, level=()):
    assert isinstance(spec, dict), \
        f'bad locale spec at {level}: must be {dict}, not {type(spec)}'
    if not isinstance(data, dict):
        raise Nonconforming(
            f'object at {level} must be dict, not {type(data)}'
        )
    missing_keys = set(spec.keys()) - set(data.keys())
    if missing_keys:
        raise Nonconforming(f'dict at {level} is missing keys {missing_keys}')
    extra_keys = set(data.keys()) - set(spec.keys())
    if extra_keys:
        raise Nonconforming(f'dict at {level} has extra keys {extra_keys}')
    for key, subspec in spec.items():
        subdata = data[key]
        if isinstance(subspec, dict):
            _conform_to_spec(subdata, subspec, level + (key,))
        else:
            assert isinstance(subspec, type | types.UnionType), \
                f'bad locale spec at {level + (key,)}: must be {dict | type}, not {type(subspec)}'
            if not isinstance(subdata, subspec):
                raise Nonconforming(
                    f'value at {level + (key,)} must be {subspec}, not {type(subdata)}'
                )

def validate_locale(locale):
    return _conform_to_spec(locale, SPEC)
