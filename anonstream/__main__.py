import argparse
import os

import uvicorn

from anonstream import create_app

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=26)
parser = argparse.ArgumentParser(
    'python -m anonstream',
    description='Start the anonstream webserver locally.',
    formatter_class=formatter,
)
parser.add_argument(
    '--config', '-c',
    metavar='FILE',
    default=os.environ.get('ANONSTREAM_CONFIG', 'config.toml'),
    help=(
        'location of config.toml '
        '(default: $ANONSTREAM_CONFIG or ./config.toml)'
    ),
)
parser.add_argument(
    '--port', '-p',
    type=int,
    default=5051,
    help='bind webserver to this port (default: 5051)',
)
args = parser.parse_args()

app = create_app(args.config)
uvicorn.run(app, port=args.port)
