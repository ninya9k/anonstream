import argparse
import os

import toml
import uvicorn

from anonstream import create_app

DEFAULT_PORT = 5051
DEFAULT_CONFIG = 'config.toml'

def want_rel(path):
    '''
    Prepend './' to relative paths.
    >>> want_rel('/some/abs/path')
    '/some/abs/path'
    >>> want_rel('config.toml')
    './config.toml'
    '''
    if os.path.isabs(path):
        return path
    else:
        return os.path.join('.', path)

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
        f'(default: $ANONSTREAM_CONFIG or {want_rel(DEFAULT_CONFIG)})'
    ),
)
parser.add_argument(
    '--port', '-p',
    type=int,
    default=DEFAULT_PORT,
    help=f'bind webserver to this port (default: {DEFAULT_PORT})',
)
args = parser.parse_args()

with open(args.config) as fp:
    config = toml.load(fp)
app = create_app(config)
uvicorn.run(app, port=args.port)
