"""
Centralized Error Handling Module.
Defines custom API exceptions and registers global Flask error handlers
returning standardized JSON envelopes for all HTTP error codes.
"""

import logging
from typing import Any, Dict, Optional
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("exam_planner.errors")


class APIError(Exception):
    """Base class for application-level API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        errors: Optional[Any] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.errors = errors
        self.payload = payload

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        rv = dict(self.payload or ())
        rv["success"] = False
        rv["message"] = self.message
        if self.errors is not None:
            rv["errors"] = self.errors
        return rv


class BadRequestError(APIError):
    """400 Bad Request."""
    def __init__(self, message: str = "Bad request.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=400, errors=errors)


class UnauthorizedError(APIError):
    """401 Unauthorized."""
    def __init__(self, message: str = "Authentication required.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=401, errors=errors)


class ForbiddenError(APIError):
    """403 Forbidden."""
    def __init__(self, message: str = "Access forbidden.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=403, errors=errors)


class NotFoundError(APIError):
    """404 Not Found."""
    def __init__(self, message: str = "Resource not found.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=404, errors=errors)


class ConflictError(APIError):
    """409 Conflict (e.g. duplicate resource or constraint violation)."""
    def __init__(self, message: str = "Conflict with existing data.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=409, errors=errors)


class ValidationError(APIError):
    """422 Unprocessable Entity / Validation failure."""
    def __init__(self, message: str = "Validation error.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=422, errors=errors)


class InternalServerError(APIError):
    """500 Internal Server Error."""
    def __init__(self, message: str = "An unexpected error occurred.", errors: Optional[Any] = None):
        super().__init__(message=message, status_code=500, errors=errors)


def register_error_handlers(app: Flask) -> None:
    """
    Registers global error handlers to ensure all errors return
    consistent JSON envelopes with proper HTTP status codes.
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handles custom application exceptions."""
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error: IntegrityError):
        """
        Catches database uniqueness/foreign key integrity violations
        without exposing raw database internal details or credentials.
        """
        logger.warning(f"Database integrity violation at {request.path}: {error.orig}")
        orig_msg = str(error.orig).lower() if error.orig else ""

        if "unique constraint" in orig_msg or "duplicate key" in orig_msg:
            message = "A record with this identifier or unique attribute already exists."
        elif "foreign key constraint" in orig_msg:
            message = "Referenced entity does not exist or cannot be removed due to dependent records."
        else:
            message = "Database constraint violation occurred."

        return jsonify({
            "success": False,
            "message": message
        }), 409

    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error: SQLAlchemyError):
        """Catches general database errors."""
        logger.error(f"Database error at {request.path}: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "A database operation error occurred. Please try again."
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handles standard Werkzeug HTTP exceptions (404, 405, 400, etc.)."""
        return jsonify({
            "success": False,
            "message": error.description
        }), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        """
        Catch-all handler for unhandled exceptions.
        Logs full traceback securely and returns generic 500 JSON.
        """
        logger.error(f"Unhandled exception at {request.path}: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "An unexpected internal server error occurred. Please contact the system administrator."
        }), 500
