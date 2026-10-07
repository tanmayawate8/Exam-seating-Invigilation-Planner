"""
Authentication Routes Module.
Exposes REST endpoints for user login, logout, session querying, and password management.
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required

from app.schemas.auth import (
    validate_login_input,
    validate_password_change_input,
    serialize_user,
)
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/ping", methods=["GET"])
def ping():
    """Health ping for authentication routes."""
    return jsonify({
        "success": True,
        "blueprint": "auth",
        "status": "active"
    }), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Authenticates user and establishes a session.
    Payload: {"username" | "email": "...", "password": "...", "remember": bool}
    """
    body = request.get_json(silent=True) or {}
    is_valid, validation_result = validate_login_input(body)

    if not is_valid:
        return jsonify({
            "success": False,
            "message": validation_result
        }), 400

    identifier = validation_result["identifier"]
    password = validation_result["password"]
    remember = validation_result["remember"]
    ip_address = request.remote_addr

    success, user, message = AuthService.authenticate(
        identifier=identifier,
        password=password,
        remember=remember,
        ip_address=ip_address,
    )

    if not success:
        return jsonify({
            "success": False,
            "message": message
        }), 401

    return jsonify({
        "success": True,
        "message": message,
        "data": {
            "user": serialize_user(user, include_profile=True)
        }
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    POST /api/auth/logout
    Terminates the active user session.
    """
    ip_address = request.remote_addr
    success, message = AuthService.logout(current_user, ip_address=ip_address)

    return jsonify({
        "success": True,
        "message": message
    }), 200


@auth_bp.route("/me", methods=["GET"])
def get_current_user_info():
    """
    GET /api/auth/me
    Retrieves the identity and profile of the currently authenticated user.
    """
    if not current_user.is_authenticated:
        return jsonify({
            "success": False,
            "message": "Authentication required. Please log in to access this resource."
        }), 401

    return jsonify({
        "success": True,
        "message": "Current session active.",
        "data": {
            "user": serialize_user(current_user, include_profile=True)
        }
    }), 200


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """
    POST /api/auth/change-password
    Changes password for the currently authenticated user.
    Payload: {"current_password": "...", "new_password": "...", "confirm_password": "..."}
    """
    body = request.get_json(silent=True) or {}
    is_valid, validation_result = validate_password_change_input(body)

    if not is_valid:
        return jsonify({
            "success": False,
            "message": validation_result
        }), 400

    current_password = validation_result["current_password"]
    new_password = validation_result["new_password"]
    ip_address = request.remote_addr

    success, message = AuthService.change_password(
        user=current_user,
        current_password=current_password,
        new_password=new_password,
        ip_address=ip_address,
    )

    if not success:
        return jsonify({
            "success": False,
            "message": message
        }), 400

    return jsonify({
        "success": True,
        "message": message
    }), 200
