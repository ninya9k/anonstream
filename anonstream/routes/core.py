# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import math

from quart import current_app, request, render_template, abort, make_response, redirect, url_for, send_from_directory
from werkzeug.exceptions import NotFound, TooManyRequests

from anonstream.access import add_failure, pop_failure
from anonstream.captcha import get_captcha_image, get_random_captcha_digest
from anonstream.segments import segments, StopSendingSegments
from anonstream.stream import is_online, get_stream_uptime
from anonstream.user import watching, create_eyes, renew_eyes, EyesException, RatelimitedEyes, TooManyEyes
from anonstream.routes.wrappers import with_user_from, auth_required, clean_cache_headers, generate_and_add_user
from anonstream.helpers.captcha import check_captcha_digest, Answer
from anonstream.utils.security import generate_csp
from anonstream.utils.user import identifying_string

CAPTCHA_SIGNER = current_app.captcha_signer
STATIC_DIRECTORY = current_app.root_path / 'static'

@current_app.route('/')
@with_user_from(request, fallback_to_token=True)
async def home(timestamp, user_or_token):
    match user_or_token:
        case str() | None:
            failure_id = request.args.get('failure', type=int)
            response = await render_template(
                'captcha.html',
                csp=generate_csp(),
                token=user_or_token,
                digest=get_random_captcha_digest(),
                failure=pop_failure(failure_id),
            )
        case dict():
            response = await render_template(
                'home.html',
                csp=generate_csp(),
                user=user_or_token,
            )
    return response

@current_app.route('/stream.mp4')
@with_user_from(request)
async def stream(timestamp, user):
    if not is_online():
        raise NotFound('The stream is offline.')
    else:
        try:
            eyes_id = create_eyes(user, tuple(request.headers))
        except RatelimitedEyes as e:
            retry_after, *_ = e.args
            error = TooManyRequests(
                f'You have requested the stream recently.  '
                f'Try again in {retry_after:.1f} seconds.'
            )
            response = await current_app.handle_http_exception(error)
            response = await make_response(response)
            response.headers['Retry-After'] = math.ceil(retry_after)
            raise abort(response)
        except TooManyEyes as e:
            n_eyes, *_ = e.args
            raise TooManyRequests(
                f'You have made {n_eyes} concurrent requests for the stream. '
                f'End one of those before making a new request.'
            )
        else:
            def segment_read_hook(uri):
                try:
                    renew_eyes(user, eyes_id, just_read_new_segment=True)
                except EyesException as e:
                    raise StopSendingSegments(
                        f'eyes {eyes_id} not allowed: {e!r}'
                    ) from e
                print(f'{uri}: \033[37m{eyes_id}\033[0m~{identifying_string(user)}')
                watching(user)
            generator = segments(segment_read_hook, token=f'\033[35m{user["token"]}\033[0m')
            response = await make_response(generator)
            response.headers['Content-Type'] = 'video/mp4'
            response.timeout = None
    return response

@current_app.route('/login')
@auth_required
async def login():
    return redirect(url_for('home'), 303)

@current_app.route('/captcha.jpg')
@with_user_from(request, fallback_to_token=True)
async def captcha(timestamp, user_or_token):
    digest = request.args.get('digest', '')
    image = get_captcha_image(digest)
    if image is None:
        return abort(410)
    else:
        return image, {'Content-Type': 'image/jpeg'}

@current_app.post('/access')
@with_user_from(request, fallback_to_token=True)
async def access(timestamp, user_or_token):
    match user_or_token:
        case str() | None:
            token = user_or_token
            form = await request.form
            digest = form.get('digest', '')
            answer = form.get('answer', '')
            match check_captcha_digest(CAPTCHA_SIGNER, digest, answer):
                case Answer.MISSING:
                    failure_id = add_failure('Captcha is required')
                case Answer.BAD:
                    failure_id = add_failure('Captcha was incorrect')
                case Answer.EXPIRED:
                    failure_id = add_failure('Captcha has expired')
                case Answer.OK:
                    failure_id = None
                    user = generate_and_add_user(timestamp, token, verified=True)
            if failure_id is not None:
                url = url_for('home', token=token, failure=failure_id)
                raise abort(redirect(url, 303))
        case dict():
            user = user_or_token
    url = url_for('home', token=user['token'])
    return redirect(url, 303)

@current_app.route('/static/<filename>')
@with_user_from(request)
@clean_cache_headers
async def static(timestamp, user, filename):
    return await send_from_directory(STATIC_DIRECTORY, filename)
