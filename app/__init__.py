from flask import Flask
from flask_cors import CORS
from app.database import db
from config import Config

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        # Import routes and initialize them with app
        from app.routes import init_routes
        init_routes(app)
        
        # Create tables
        db.create_all()

    return app