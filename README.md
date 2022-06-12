# anonstream

Recipe for livestreaming over Tor

## Repo

The canonical location of this repo is
<https://git.076.ne.jp/ninya9k/anonstream>.

These mirrors also exist:
* <https://gitlab.com/ninya9k/anonstream>
* <https://github.com/ninya9k/anonstream>

## Setup

You must have Python 3.10 at a minimum.

Clone the repo:
```sh
git clone https://git.076.ne.jp/ninya9k/anonstream.git
cd anonstream
```

Install dependencies in a virtual environment:
```sh
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Before you run it you should edit [/config.toml][config], e.g. these
options:

* `secret_key`:
  used for cryptography, make it any long random string
  (e.g. `$ dd if=/dev/urandom bs=16 count=1 | base64`)

* `segments/directory`:
  directory containing stream segments, the default is `stream/` in
  the cloned repository

* `title/file`:
  location of the stream title, the default is `title.txt` in the
  cloned repository

* `captcha/fonts`:
  locations of fonts for the captcha, leaving it blank will use the
  default font

Run it:
```sh
python -m uvicorn app:app --port 5051
```

This will start a webserver listening on localhost port 5051.

If you go to `http://localhost:5051` in a web browser now you should see
the site.  When you started the webserver some credentials were
printed in the terminal; you can log in with those at
`http://localhost:5051/login` (requires cookies).

The only things left are (1) streaming, and (2) letting other people
access your stream.  [/STREAMING.md][streaming] has instructions for
setting up OBS Studio and a Tor onion service.  If you want to use
different streaming software and put your stream on the Internet some
other way, still read those instructions and copy the gist.

## Copying

anonstream is AGPL 3.0 or later, see
[/LICENSES/AGPL-3.0-or-later.md][licence].

### Assets

* [/anonstream/static/settings.svg][settings.svg]:
  [setting](https://thenounproject.com/icon/setting-685325/) by
  [ulimicon](https://thenounproject.com/unlimicon/) is licensed under
  [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

### Dependencies

* aiofiles <https://github.com/Tinche/aiofiles>
  ([Apache 2.0][aiofiles])

* captcha <https://github.com/lepture/captcha>
  ([BSD 3-Clause][captcha])

* itsdangerous <https://github.com/pallets/itsdangerous/>
  ([BSD 3-Clause][itsdangerous])

* m3u8 <https://github.com/globocom/m3u8>
  ([MIT][m3u8])

* quart <https://gitlab.com/pgjones/quart>
  ([MIT][quart])

* toml <https://github.com/uiri/toml>
  ([MIT][toml])

* uvicorn <https://github.com/encode/uvicorn>
  ([BSD 3-Clause][uvicorn])

* werkzeug <https://github.com/pallets/werkzeug>
  ([BSD 3-Clause][werkzeug])

[config]: https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/config.toml
[licence]: https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/LICENSES/AGPL-3.0-or-later.md
[settings.svg]: https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/anonstream/static/settings.svg
[streaming]: https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/STREAMING.md

[aiofiles]: https://github.com/Tinche/aiofiles/blob/master/LICENSE
[captcha]: https://github.com/lepture/captcha/blob/master/LICENSE
[itsdangerous]: https://github.com/pallets/itsdangerous/blob/main/LICENSE.rst
[m3u8]: https://github.com/globocom/m3u8/blob/master/LICENSE
[quart]: https://gitlab.com/pgjones/quart/-/blob/main/LICENSE
[toml]: https://github.com/uiri/toml/blob/master/LICENSE
[uvicorn]: https://github.com/encode/uvicorn/blob/master/LICENSE.md
[werkzeug]: https://github.com/pallets/werkzeug/blob/main/LICENSE.rst
