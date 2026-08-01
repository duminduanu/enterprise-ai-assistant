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
