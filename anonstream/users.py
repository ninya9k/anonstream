from quart import current_app

def get_default_name(user):
    return (
        current_app.config['DEFAULT_HOST_NAME']
        if user['broadcaster'] else
        current_app.config['DEFAULT_ANON_NAME']
    )

