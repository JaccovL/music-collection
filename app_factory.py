"""Application factory — creates and configures the Flask app."""
import logging
from flask import Flask
from extensions import db, login_manager, csrf, scheduler
from config import Config


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.collection import collection_bp
    from blueprints.wantlist import wantlist_bp
    from blueprints.admin import admin_bp
    from blueprints.api import api_bp
    from blueprints.export import export_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(collection_bp)
    app.register_blueprint(wantlist_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(export_bp)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    
    return app
