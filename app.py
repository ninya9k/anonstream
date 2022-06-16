# SPDX-FileCopyrightText: 2022 n9k <https://git.076.ne.jp/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import anonstream

config_file = os.path.join(os.path.dirname(__file__), 'config.toml')
app = anonstream.create_app(config_file)

if __name__ == '__main__':
    app.run(port=5051, debug=True)
