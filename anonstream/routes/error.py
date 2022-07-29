from quart import current_app, render_template, request
from werkzeug.exceptions import default_exceptions

from anonstream.locale import get_locale_from

for error in default_exceptions:
    async def handle(error):
        if error.description == error.__class__.description:
            error.description = None
        return (
            await render_template(
                'error.html', error=error,
                locale=get_locale_from(request)['http'],
            ), error.code
        )
    current_app.register_error_handler(error, handle)
