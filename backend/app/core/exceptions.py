"""Application-specific exceptions."""

from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RetrievalError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class LLMError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)


class ValidationError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, status_code=403)


class RateLimitError(AppError):
    def __init__(self, message: str, *, retry_after: int = 60) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AgentTimeoutError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=504)


class ToolTimeoutError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=504)


class MCPError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class AgentError(AppError):
    """Non-fatal agent orchestration failure with a user-safe message."""

    def __init__(self, message: str, *, status_code: int = 503) -> None:
        super().__init__(message, status_code=status_code)
