# anonstream

Recipe for livestreaming over Tor

## Repo

The canonical location of this repo is
<https://git.076.ne.jp/ninya9k/anonstream>.

These mirrors also exist:
* <https://gitlab.com/ninya9k/anonstream>
* <https://github.com/ninya9k/anonstream>

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

[config]:       https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/config.toml
[licence]:      https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/LICENSES/AGPL-3.0-or-later.md
[settings.svg]: https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/anonstream/static/settings.svg
[streaming]:    https://git.076.ne.jp/ninya9k/anonstream/src/branch/master/STREAMING.md

[aiofiles]: https://github.com/Tinche/aiofiles/blob/master/LICENSE
[captcha]: https://github.com/lepture/captcha/blob/master/LICENSE
[itsdangerous]: https://github.com/pallets/itsdangerous/blob/main/LICENSE.rst
[m3u8]: https://github.com/globocom/m3u8/blob/master/LICENSE
[quart]: https://gitlab.com/pgjones/quart/-/blob/main/LICENSE
[toml]: https://github.com/uiri/toml/blob/master/LICENSE
[uvicorn]: https://github.com/encode/uvicorn/blob/master/LICENSE.md
[werkzeug]: https://github.com/pallets/werkzeug/blob/main/LICENSE.rst
