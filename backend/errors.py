"""Centralized error handling for E9.

Every error surfaced to the client uses the same envelope:

    {"success": false, "error": {"code": "...", "message": "..."}}

Codes are stable and short; messages are human-friendly, never technical.
"""

# --- stable error codes ---
VALIDATION_ERROR = "VALIDATION_ERROR"
INVALID_REQUEST = "INVALID_REQUEST"
AUTH_REQUIRED = "AUTH_REQUIRED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
SERVER_ERROR = "SERVER_ERROR"
EMPTY_INPUT = "EMPTY_INPUT"
REPORT_TOO_SHORT = "REPORT_TOO_SHORT"
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
RUBRIC_REQUIRED = "RUBRIC_REQUIRED"
AI_FAILURE = "AI_FAILURE"
TIMEOUT = "TIMEOUT"
AI_NOT_CONFIGURED = "AI_NOT_CONFIGURED"

# --- short, human-friendly messages (no jargon, no stack traces) ---
MESSAGES = {
    VALIDATION_ERROR: "Please check your input. Some fields are missing or incorrect.",
    INVALID_REQUEST: "Invalid request. Please try again.",
    AUTH_REQUIRED: "You are not logged in. Please login first.",
    FORBIDDEN: "You are not allowed to do this action.",
    NOT_FOUND: "Requested data not found.",
    SERVER_ERROR: "Something went wrong on our side. Please try again later.",
    EMPTY_INPUT: "Report cannot be empty.",
    REPORT_TOO_SHORT: "Report is too short. Minimum 200 characters required.",
    LIMIT_EXCEEDED: "Report is too long. Maximum allowed is 10,000 words.",
    RUBRIC_REQUIRED: "Please select a rubric before scoring.",
    AI_FAILURE: "The system is taking too long. Please try again.",
    TIMEOUT: "The system is taking too long. Please try again.",
    AI_NOT_CONFIGURED: "Scoring engine is not configured yet. Please try again later.",
}

# HTTP status -> default error code
STATUS_CODES = {
    400: INVALID_REQUEST,
    401: AUTH_REQUIRED,
    403: FORBIDDEN,
    404: NOT_FOUND,
    500: SERVER_ERROR,
}


class AppError(Exception):
    """Business error carrying a stable code and a friendly message."""

    def __init__(self, code, message=None, status_code=400):
        self.code = code
        self.message = message or MESSAGES.get(code, MESSAGES[INVALID_REQUEST])
        self.status_code = status_code
        super().__init__(self.message)


def error_response(code, message):
    return {"success": False, "error": {"code": code, "message": message}}


def is_timeout(exc):
    """Best-effort detection of provider/network timeouts (builtin or SDK)."""
    name = type(exc).__name__.lower()
    return (isinstance(exc, TimeoutError) or "timeout" in name
            or "connection" in name or "read error" in name)
