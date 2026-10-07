"""
Flask Extensions Initialization Module.
Declares extension instances unbound to any specific application instance
to prevent circular dependencies (Application Factory Pattern).
"""

from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# SQLAlchemy ORM instance
db = SQLAlchemy()

# Flask-Migrate database migration manager
migrate = Migrate()

# Flask-Login user session manager
login_manager = LoginManager()

# Default login view configuration for Flask-Login
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this resource."
login_manager.login_message_category = "warning"


@login_manager.unauthorized_handler
def unauthorized_callback():
    """Returns standardized JSON 401 for unauthorized API requests."""
    return jsonify({
        "success": False,
        "message": "Authentication required. Please log in to access this resource."
    }), 401
