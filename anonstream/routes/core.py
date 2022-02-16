from quart import current_app, request, render_template, redirect, url_for

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
