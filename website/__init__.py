from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask_compress import Compress
import secrets

# Override HTTP headers globally https://stackoverflow.com/a/46858238
class LocalFlask(Flask):
    def process_response(self, response):
        # Every response will be processed here first
        super().process_response(response)
        response.headers['Server'] = 'Werkzeug'
        return response


def create_app():
    app = LocalFlask(__name__)

    compress = Compress()
    compress.init_app(app)

    app.auth = HTTPBasicAuth()

    @app.auth.verify_password
    def verify_password(username, password):
        if username == 'broadcaster' and password == broadcaster_pw:
            return username

    broadcaster_pw = secrets.token_urlsafe(6)
    print('Broadcaster password:', broadcaster_pw)

    with app.app_context():
        from website import routes

    return app
