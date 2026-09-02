"""Application factory — creates and configures the Flask app."""
import logging
from flask import Flask
from extensions import db, login_manager, csrf, scheduler


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    from config import Config
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    
    # User loader for Flask-Login
    from models import User, utc_to_amsterdam
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Phase 5.1: Rate limiting
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )
    
    # Phase 5.3: Content Security Policy
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' https: data:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'none'",
        'form-action': "'self'",
        'base-uri': "'self'",
    }
    
    @app.context_processor
    def inject_csp_nonce():
        from flask import g
        nonce = getattr(g, 'csp_nonce', '')
        return {'csp_nonce': nonce}
    
    @app.after_request
    def set_security_headers(response):
        # CSP Header
        csp_string = '; '.join(f'{key} {value}' for key, value in csp.items())
        response.headers['Content-Security-Policy'] = csp_string
        
        # Security headers
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response
    
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
    
    # Jinja globals
    from app_utils import get_setting
    app.jinja_env.globals['get_setting'] = get_setting
    app.jinja_env.globals['utc_to_amsterdam'] = utc_to_amsterdam
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    
    return app
