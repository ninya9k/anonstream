import secrets

def generate_csp():
    '''
    Generate a random Content Secuity Policy nonce.
    '''
    return secrets.token_urlsafe(16)
