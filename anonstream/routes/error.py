from quart import current_app, render_template

from werkzeug.exceptions import default_exceptions

for error in default_exceptions:
    async def handle(error):
        return await render_template('error.html', error=error), error.code
    current_app.register_error_handler(error, handle)
