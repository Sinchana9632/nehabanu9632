import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Initialize SQLAlchemy with a custom base
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    # Create the app
    app = Flask(__name__, 
               template_folder='templates',
               static_folder='static')
    
    # Configure the app
    app.config["SECRET_KEY"] = os.environ.get("SESSION_SECRET", "mindcare-ai-secret-key-2024")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///mindcare.db")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    with app.app_context():
        # Import models
        from . import models
        
        # Import routes
        from . import routes
        
        # Create database tables
        db.create_all()
    
    return app