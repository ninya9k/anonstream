# SPDX-FileCopyrightText: 2022 n9k <https://gitler.moe/ninya9k>
# SPDX-License-Identifier: AGPL-3.0-or-later

import secrets

def generate_csp():
    '''
    Generate a random Content Secuity Policy nonce.
    '''
    return secrets.token_urlsafe(16)
