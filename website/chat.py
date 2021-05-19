import secrets
import time
import unicodedata
from collections import deque
from datetime import datetime

import website.utils.captcha as captcha_util
import website.utils.tripcode as tripcode
import website.viewership as viewership
from website.constants import BROADCASTER_TOKEN, MESSAGE_MAX_LENGTH, CHAT_MAX_STORAGE, CHAT_TIMEOUT, FLOOD_PERIOD, FLOOD_THRESHOLD, CAPTCHA_LIFETIME, \
                              NOTES, N_NONE, N_TOKEN_EMPTY, N_MESSAGE_EMPTY, N_MESSAGE_LONG, N_BANNED, N_TOOFAST, N_FLOOD, N_CAPTCHA_MISSING, N_CAPTCHA_WRONG, N_CAPTCHA_USED, N_CAPTCHA_EXPIRED, N_CAPTCHA_RANDOM, N_CONFIRM, N_APPEAR_OK, N_APPEAR_FAIL

from pprint import pprint

messages = deque() # messages are stored from most recent on the left to least recent on the right
captchas = {} # captchas that have been used already
viewers = viewership.viewers
nonces = {}

def behead_chat():
    while len(messages) > CHAT_MAX_STORAGE:
        messages.pop()

def new_nonce():
    now = int(time.time())
    nonce = secrets.token_hex(8)
    with viewership.lock:
        remove_expired_nonces()
        nonces[nonce] = now
    return nonce

def remove_expired_captchas():
    now = int(time.time())
    to_pop = []
    for ciphertext in captchas:
        timestamp = captchas[ciphertext]
        if timestamp < now - CAPTCHA_LIFETIME:
            to_pop.append(ciphertext)
    for ciphertext in to_pop:
        captchas.pop(ciphertext)

def remove_expired_nonces():
    now = int(time.time())
    to_pop = []
    for nonce in nonces:
        timestamp = nonces[nonce]
        if timestamp < now - CAPTCHA_LIFETIME:
            to_pop.append(nonce)
    for nonce in to_pop:
        nonces.pop(nonce)

def _comment(text, token, c_response, c_ciphertext, nonce):
    now = int(time.time())
    if not token:
        return N_TOKEN_EMPTY
    if not text:
        return N_MESSAGE_EMPTY
    if len(text) >= MESSAGE_MAX_LENGTH:
        return N_MESSAGE_LONG

    viewership.setdefault(token)

    # remove record of old comments
    for t in viewers[token]['recent_comments'].copy():
        if t < now - FLOOD_PERIOD:
            viewers[token]['recent_comments'].remove(t)

    pprint(viewers)

    if viewers[token]['banned']:
        return N_BANNED

    # check that the commenter hasn't acidentally sent the same request twice
    remove_expired_nonces()
    try:
        nonces.pop(nonce)
    except KeyError:
        return N_CONFIRM

    # check captcha
    if not viewers[token]['verified']:
        if c_response and c_ciphertext:
            try:
                c_timestamp = captcha_util.get_creation_time(c_ciphertext, c_response)
            # captcha answer is incorrect
            except captcha_util.Incorrect as e:
                c_timestamp = e.args[0]
                remove_expired_captchas()
                captchas[c_ciphertext] = c_timestamp
                return N_CAPTCHA_WRONG
            # captcha is not genuine
            except captcha_util.FakeCiphertext:
                return N_CAPTCHA_MISSING
            # captcha has expired
            if c_timestamp + CAPTCHA_LIFETIME < now:
                remove_expired_captchas()
                return N_CAPTCHA_EXPIRED
            # captcha has been used already
            if c_ciphertext in captchas:
                return N_CAPTCHA_USED
            # captcha was correct, everything is fine
            remove_expired_captchas()
            captchas[c_ciphertext] = c_timestamp
        else:
            return N_CAPTCHA_MISSING

    if secrets.randbelow(50) == 0:
        viewers[token]['verified'] = False
        return N_CAPTCHA_RANDOM
    if now < viewers[token]['last_comment'] + CHAT_TIMEOUT:
        return N_TOOFAST
    if len(viewers[token]['recent_comments']) + 1 >= FLOOD_THRESHOLD:
        viewers[token]['verified'] = False
        return N_FLOOD

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
    return N_NONE

def comment(text, token, c_response, c_ciphertext, nonce):
    with viewership.lock:
        failure_reason = _comment(text, token, c_response, c_ciphertext, nonce)
        viewership.setdefault(BROADCASTER_TOKEN)
        viewers[BROADCASTER_TOKEN]['verified'] = True
    print(f'Comment submission (token={token}, name={viewers[token]["nickname"]!r}, tag={viewers[token]["tag"]})', 'SUCCEEDED' if failure_reason == N_NONE else f'FAILED with note {NOTES[failure_reason]!r}')
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
    c_src, c_ciphertext = captcha_util.gen_captcha()
    return {'src': c_src, 'ciphertext': c_ciphertext}

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

    # order from least to most recent
    messages.reverse()

    # TODO: chat commands e.g. !uptime; try to make it so responses always follow the message with the command, so not split over a date separator

    # add dates between messages that cross over a day boundary
    to_insert = []
    previous_message = None
    for index, message in enumerate(messages):
        if message.get('special') or not _is_visible(message):
            continue
        if previous_message and message['date'] != previous_message['date']:
            to_insert.append(index)
        previous_message = message

    to_insert.reverse()
    for index in to_insert:
        messages.insert(index, {'special': 'date', 'content': messages[index]['date']})

    # add date at the top if messages span several days
    if to_insert:
        for index, first_visible_message in enumerate(messages):
            if _is_visible(message):
                break
        else:
            index = None
        if index != None:
            messages.insert(index, {'special': 'date', 'content': first_visible_message['date']})

    # revert back to original ordering
    messages.reverse()
