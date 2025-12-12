import os
from flask import Flask
from .config import Config

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    app.config['SECRET_KEY'] = os.urandom(24)
    # register blueprints / routes
    # from .routes_test import main_bp
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app



# python run.py