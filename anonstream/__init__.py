# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from collections import OrderedDict

from quart_compress import Compress

from anonstream.config import update_flask_from_toml
from anonstream.emote import load_emote_schema
from anonstream.quart import Quart
from anonstream.utils.captcha import create_captcha_factory, create_captcha_signer
from anonstream.utils.user import generate_blank_allowedness

__version__ = '1.6.9'

def create_app(toml_config):
    app = Quart('anonstream', static_folder=None)
    app.version = __version__

    auth_password = update_flask_from_toml(toml_config, app.config)
    print('Broadcaster username:', app.config['AUTH_USERNAME'])
    print('Broadcaster password:', auth_password)

    # Nicer whitespace in templates
    app.jinja_options['trim_blocks'] = True
    app.jinja_options['lstrip_blocks'] = True

    # Compress some responses
    Compress(app)
    app.config.update({
        'COMPRESS_MIN_SIZE': 2048,
        'COMPRESS_LEVEL': 9,
    })

    # Global state: messages, users, captchas, etc.
    app.messages_by_id = OrderedDict()
    app.messages = app.messages_by_id.values()

    app.users_by_token = {}
    app.users = app.users_by_token.values()

    app.captchas = OrderedDict()
    app.captcha_factory = create_captcha_factory(app.config['CAPTCHA_FONTS'])
    app.captcha_signer = create_captcha_signer(app.config['SECRET_KEY'])

    app.failures = OrderedDict() # access captcha failures
    app.allowedness = generate_blank_allowedness()

    # Read emote schema
    try:
        app.emotes = load_emote_schema(app.config['EMOTE_SCHEMA'])
    except (OSError, json.JSONDecodeError) as e:
        raise AssertionError(f'couldn\'t load emote schema: {e!r}') from e

    # State for tasks
    app.users_update_buffer = set()
    app.stream_title = None
    app.stream_uptime = None
    app.stream_viewership = None
    app.last_info_task = None

    # asyncio tasks to be cancelled on shutdown
    app.tasks = set()

    # Queues for event socket clients
    app.event_queues = set()

    @app.after_serving
    async def shutdown():
        # Cancel started asyncio tasks that would otherwise block shutdown
        # The asyncio tasks we create are:
        #   * quart background tasks awaiting asyncio.sleep()
        for task in app.tasks:
            task.cancel()

    @app.before_serving
    async def startup():
        # Create routes and background tasks
        import anonstream.routes
        import anonstream.tasks

        # Start control server
        if app.config['SOCKET_CONTROL_ENABLED']:
            from anonstream.control.server import start_control_server_at
            async def start_control_server():
                return await start_control_server_at(
                    app.config['SOCKET_CONTROL_ADDRESS']
                )
            app.add_background_task(start_control_server)

        # Start event server
        if app.config['SOCKET_EVENT_ENABLED']:
            from anonstream.events import start_event_server_at
            async def start_event_server():
                return await start_event_server_at(
                    app.config['SOCKET_EVENT_ADDRESS']
                )
            app.add_background_task(start_event_server)

    return app
