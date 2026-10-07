"""
Flask Application Factory Module.
Online Exam Seating & Invigilation Planner (Teachers College).

Orchestrates:
run.py -> create_app() -> configuration -> extensions -> blueprints -> routes
"""

import os
from flask import Flask, jsonify
from app.config import config_by_name
from app.extensions import db, migrate, login_manager
from app.routes import register_blueprints
from app.utils.errors import register_error_handlers
from app import models as _models


def create_app(config_name: str | None = None) -> Flask:
    """
    Flask Application Factory.
    Creates, configures, and returns a new Flask application instance.

    :param config_name: Environment key ('development', 'testing', 'production')
    :return: Fully configured Flask application instance
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)

    # 1. Load Environment Configuration
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # 2. Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # 3. Register Error Handlers
    register_error_handlers(app)

    # 4. Register All Application Blueprints
    register_blueprints(app)

    # 4. Root Health Check & Information Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "success": True,
            "service": "Online Exam Seating & Invigilation Planner API",
            "environment": config_name,
            "status": "healthy"
        }), 200

    return app
