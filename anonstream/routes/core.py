from quart import current_app, request, render_template, abort, make_response, redirect, url_for, abort

from anonstream.captcha import get_captcha_image
from anonstream.segments import segments
from anonstream.stream import is_online, get_stream_uptime
from anonstream.user import watched
from anonstream.routes.wrappers import with_user_from, auth_required

@current_app.route('/')
@with_user_from(request)
async def home(user):
    return await render_template('home.html', user=user)

@current_app.route('/stream.mp4')
@with_user_from(request)
async def stream(user):
    if not is_online():
        return abort(404)

    def segment_read_hook(uri):
        print(f'{uri}: {user["token"]}')
        watched(user)

    generator = segments(segment_read_hook, token=user['token'])
    response = await make_response(generator)
    response.headers['Content-Type'] = 'video/mp4'
    response.timeout = None
    return response

@current_app.route('/login')
@auth_required
async def login():
    return redirect(url_for('home'))

@current_app.route('/captcha.jpg')
@with_user_from(request)
async def captcha(user):
    digest = request.args.get('digest', '')
    image = get_captcha_image(digest)
    if image is None:
        return abort(410)
    else:
        return image, {'Content-Type': 'image/jpeg'}
