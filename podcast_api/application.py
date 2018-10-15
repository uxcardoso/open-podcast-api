from flask import Flask
from flask_cors import CORS


def create_app(app_name='PODCAST_API'):
    app = Flask(app_name)
    CORS(app)
    app.config.from_object('podcast_api.config.BaseConfig')

    from podcast_api.api import api
    app.register_blueprint(api, url_prefix='/v1')

    from podcast_api.models import db
    db.init_app(app)

    return app
