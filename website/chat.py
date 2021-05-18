import secrets
import time
import unicodedata
from collections import deque
from datetime import datetime

import website.utils.captcha as captcha_util
import website.utils.tripcode as tripcode
import website.viewership as viewership
from website.constants import BROADCASTER_TOKEN, MESSAGE_MAX_LENGTH, CHAT_MAX_STORAGE, CHAT_TIMEOUT, FLOOD_PERIOD, FLOOD_THRESHOLD, \
                              NOTES, N_NONE, N_TOKEN_EMPTY, N_MESSAGE_EMPTY, N_MESSAGE_LONG, N_BANNED, N_TOOFAST, N_FLOOD, N_CAPTCHA_MISSING, N_CAPTCHA_WRONG, N_CAPTCHA_RANDOM, N_CONFIRM, N_APPEAR_OK, N_APPEAR_FAIL

from pprint import pprint

messages = deque() # messages are stored from most recent on the left to least recent on the right
captchas = {}
viewers = viewership.viewers
nonces = set()

def behead_chat():
    while len(messages) > CHAT_MAX_STORAGE:
        messages.pop()

def new_nonce():
    nonce = secrets.token_hex(8)
    with viewership.lock:
        nonces.add(nonce)
    return nonce

def comment(text, token, c_response, c_token, nonce):
    failure_reason = N_NONE
    with viewership.lock:
        now = int(time.time())
        if not token:
            failure_reason = N_TOKEN_EMPTY
        elif not text:
            failure_reason = N_MESSAGE_EMPTY
        elif len(text) >= MESSAGE_MAX_LENGTH:
            failure_reason = N_MESSAGE_LONG
        else:
            viewership.setdefault(token)
            # remove record of old comments
            for t in viewers[token]['recent_comments'].copy():
                if t < now - FLOOD_PERIOD:
                    viewers[token]['recent_comments'].remove(t)

            pprint(viewers)

            if viewers[token]['banned']:
                failure_reason = N_BANNED
            elif not viewers[token]['verified'] and c_token not in captchas:
                failure_reason = N_CAPTCHA_MISSING
            elif not viewers[token]['verified'] and captchas[c_token] != c_response:
                failure_reason = N_CAPTCHA_WRONG
            elif secrets.randbelow(50) == 0:
                failure_reason = N_CAPTCHA_RANDOM
                viewers[token]['verified'] = False
            elif now < viewers[token]['last_comment'] + CHAT_TIMEOUT:
                failure_reason = N_TOOFAST
            elif len(viewers[token]['recent_comments']) + 1 >= FLOOD_THRESHOLD:
                failure_reason = N_FLOOD
                viewers[token]['verified'] = False
            else:
                try:
                    nonces.remove(nonce)
                except KeyError:
                    failure_reason = N_CONFIRM
                else:
                    dt = datetime.utcfromtimestamp(now)
                    messages.appendleft({'text': text,
                                         'viewer': viewers[token],
                                         'id': f'{token}-{secrets.token_hex(4)}',
                                         'hidden': False,
                                         'time': dt.strftime('%H:%M'),
                                         'timestamp': dt.strftime('%F %T'),
                                         'date': dt.strftime('%F')})
                    viewers[token]['last_comment'] = now
                    viewers[token]['recent_comments'].append(now)
                    viewers[token]['verified'] = True
                    behead_chat()

    viewership.setdefault(BROADCASTER_TOKEN)
    viewers[BROADCASTER_TOKEN]['verified'] = True
    return failure_reason

def mod_chat(message_ids, hide, ban, ban_and_purge):
    purge  = ban_and_purge
    ban    = ban_and_purge or ban

    with viewership.lock:
        if ban:
            banned = {message_id.split('-')[0] for message_id in message_ids}
            for token in banned:
                viewers[token]['banned'] = True

        for message in messages:
            if hide and message['id'] in message_ids:
                message['hidden'] = True
            if purge and message['viewer']['token'] in banned:
                message['hidden'] = True

        viewership.setdefault(BROADCASTER_TOKEN)
        viewers[BROADCASTER_TOKEN]['banned'] = False

def mod_users(tokens, banned):
    print('A' * 10, tokens, banned)
    with viewership.lock:
        for token in tokens:
            viewers[token]['banned'] = banned

def get_captcha(token):
    viewership.setdefault(token)
    if viewers[token]['verified']:
        return None
    c_src, c_answer = captcha_util.gen_captcha()
    c_token = secrets.token_hex(8)
    captchas[c_token] = c_answer
    return {'src': c_src, 'token': c_token}

def set_nickname(nickname, token):
    viewership.setdefault(token)

    nickname = ''.join(char if unicodedata.category(char) != 'Cc' else ' ' for char in nickname).strip()
    if len(nickname) > 24:
        return N_APPEAR_FAIL, False

    if len(nickname) == 0 or nickname == viewership.default_nickname(token):
        nickname = None

    viewers[token]['nickname'] = nickname
    return N_APPEAR_OK, True

def set_tripcode(password, token):
    if len(password) > 256:
        return N_APPEAR_FAIL, False
    viewers[token]['tripcode'] = tripcode.gen_tripcode(password)
    return N_APPEAR_OK, True

def remove_tripcode(token):
    viewers[token]['tripcode'] = tripcode.default()
    return N_APPEAR_OK, True

def decorate(messages):
    '''
    add extra stuff to a list of messages, e.g. date, chat command responses
    '''
    def _is_visible(message):
        # uncomment the end part once the broadcaster can see hidden comments
        return not message['hidden'] # or token == BROADCASTER_TOKEN

    first_visible_message = None
    final_visible_message = None
    for message in messages:
        if _is_visible(message):
            final_visible_message = message
            break
    messages.reverse()
    for message in messages:
        if _is_visible(message):
            first_visible_message = message
            break

    # if there are no messages, do nothing
    if first_visible_message == None or final_visible_message == None:
        return

    # TODO: chat commands e.g. !uptime; try to make it so responses always follow the message with the command, so not split over a date separator

    # add date at the top if necessary
    if first_visible_message['date'] != final_visible_message['date']:
        messages.insert(0, {'special': 'date', 'content': first_visible_message['date']})

    # add dates between messages that cross over a day boundary
    to_insert = []
    previous_message = None
    for index, message in enumerate(messages):
        if message.get('special'):
            continue
        if previous_message and message['date'] != previous_message['date']:
            to_insert.append(index)
        previous_message = message

    to_insert.reverse()
    for index in to_insert:
        messages.insert(index, {'special': 'date', 'content': messages[index]['date']})

    # revert back to original ordering
    messages.reverse()
