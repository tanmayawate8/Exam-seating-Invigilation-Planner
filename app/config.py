"""
Application Configuration Module for Online Exam Seating & Invigilation Planner.
Defines environment-specific settings (Development, Testing, Production).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project (exam-planner root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration containing default settings across all environments."""

    # Secret key for signing sessions and CSRF tokens
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "fallback-dev-secret-key-teachers-college-2026"
    )

    # SQLAlchemy Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/exam_planner_db",
    )

    # Session and Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Enabled in ProductionConfig
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False  # Enabled in ProductionConfig
    REMEMBER_COOKIE_DURATION = 86400  # 1 day in seconds


class DevelopmentConfig(Config):
    """Configuration for local development."""

    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Configuration for automated test execution."""

    DEBUG = False
    TESTING = True

    # Use dedicated test database or fallback to SQLite in-memory for testing
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:",
    )

    # Disable CSRF token verification during test requests
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Configuration for production deployment."""

    DEBUG = False
    TESTING = False

    # Enforce HTTPS-only secure cookies in production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        secret = os.environ.get("SECRET_KEY")
        if not secret or "dev" in secret.lower() or "fallback" in secret.lower():
            raise ValueError(
                "CRITICAL: A secure SECRET_KEY must be set in the environment for Production!"
            )


# Configuration registry mapping string names to config classes
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
