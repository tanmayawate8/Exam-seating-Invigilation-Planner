"""
Standard API Response Envelopes Module.
Provides uniform JSON success responses across all REST controllers.
"""

from typing import Any, Dict, Optional
from flask import jsonify, Response


def success_response(
    data: Optional[Any] = None,
    message: str = "Operation completed successfully.",
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> tuple[Response, int]:
    """
    Constructs a uniform JSON success response envelope:
    {
        "success": true,
        "message": "...",
        "data": { ... } | [ ... ],
        "meta": { "pagination": ... }  (optional)
    }
    """
    envelope: Dict[str, Any] = {
        "success": True,
        "message": message,
    }
    if data is not None:
        envelope["data"] = data
    if meta is not None:
        envelope["meta"] = meta

    return jsonify(envelope), status_code
