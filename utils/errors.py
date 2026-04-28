"""
Application Error Hierarchy
============================

Custom exception classes that map to HTTP status codes and provide
structured error responses. Used by the error handler middleware
in utils/error_handlers.py and the @handle_route_errors decorator
in routes/decorators.py.

Usage:
    from utils.errors import NotFoundError, ValidationError

    # In a route handler:
    raise NotFoundError("Volunteer not found", detail=f"id={volunteer_id}")

    # In an import loop (per-record resilience):
    raise ImportRecordError(
        "Failed to process volunteer",
        record_id=row.get("Id"),
        detail=str(e),
    )
"""


class AppError(Exception):
    """Base application error with HTTP status code and safe user message.

    Attributes:
        status_code: HTTP status code to return (default 500).
        safe_message: Message safe to show to end users / return in JSON.
        detail: Internal debug information logged but NOT exposed to users.
    """

    status_code = 500
    default_message = "An internal error occurred"

    def __init__(self, message=None, *, detail=None, status_code=None):
        self.safe_message = message or self.default_message
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.safe_message)


class NotFoundError(AppError):
    """Resource not found (404)."""

    status_code = 404
    default_message = "The requested resource was not found"


class ValidationError(AppError):
    """Invalid input or business rule violation (400)."""

    status_code = 400
    default_message = "Invalid input"


class AuthorizationError(AppError):
    """Insufficient permissions (403)."""

    status_code = 403
    default_message = "You do not have permission to perform this action"


class ExternalServiceError(AppError):
    """External service failure — Salesforce, email provider, etc. (502)."""

    status_code = 502
    default_message = "An external service is temporarily unavailable"


class DatabaseError(AppError):
    """Database operation failure — wraps SQLAlchemy errors (500)."""

    status_code = 500
    default_message = "A database error occurred"


class ImportRecordError(AppError):
    """Per-record import failure with structured context.

    Used inside import loops where individual record failures
    should be logged but not halt the entire batch.

    Attributes:
        record_id: Identifier of the failed record (e.g. Salesforce ID).
    """

    status_code = 500
    default_message = "Failed to process import record"

    def __init__(self, message=None, *, record_id=None, detail=None, status_code=None):
        self.record_id = record_id
        super().__init__(message, detail=detail, status_code=status_code)
