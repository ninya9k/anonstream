from quart import current_app, request, render_template, redirect, url_for, abort

from anonstream.captcha import get_captcha_image
from anonstream.segments import CatSegments, Offline
from anonstream.routes.wrappers import with_user_from, auth_required

@current_app.route('/')
@with_user_from(request)
async def home(user):
    return await render_template('home.html', user=user)

@current_app.route('/stream.mp4')
@with_user_from(request)
async def stream(user):
    try:
        cat_segments = CatSegments(
            directory_cache=current_app.segments_directory_cache,
            token=user['token']
        )
    except Offline:
        return 'offline', 404
    response = await make_response(cat_segments.stream())
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
        return image
