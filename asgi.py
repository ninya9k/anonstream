# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

if __name__ == '__main__':
    import sys
    message = (
        'To start anonstream, run one of:\n'
        ' $ python -m anonstream\n'
        ' $ python -m uvicorn asgi:create_app --factory --port 5051\n'
    )
    print(message, file=sys.stderr, end='')
    exit(1)

import os
import toml
import anonstream

config_file = os.environ.get(
    'ANONSTREAM_CONFIG',
    os.path.join(os.path.dirname(__file__), 'config.toml'),
)

def create_app():
    with open(config_file) as fp:
        config = toml.load(fp)
    return anonstream.create_app(config)
