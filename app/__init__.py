from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from app.database import db
from config import Config

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)        # ← this line was missing

    with app.app_context():
        from app.routes import init_routes
        init_routes(app)

    return app