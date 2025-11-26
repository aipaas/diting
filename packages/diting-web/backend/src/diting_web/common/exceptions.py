"""Custom exceptions."""


class DiTingWebException(Exception):
    """Base exception for DiTing Web."""

    def __init__(self, message: str, code: int = 400) -> None:
        """Initialize exception."""
        super().__init__(message)
        self.message = message
        self.code = code


class AuthenticationError(DiTingWebException):
    """Authentication error."""

    def __init__(self, message: str = "Authentication failed") -> None:
        """Initialize exception."""
        super().__init__(message, code=401)


class AuthorizationError(DiTingWebException):
    """Authorization error."""

    def __init__(self, message: str = "Permission denied") -> None:
        """Initialize exception."""
        super().__init__(message, code=403)


class PermissionDeniedError(AuthorizationError):
    """Permission denied error (alias for AuthorizationError)."""

    pass


class ResourceNotFoundError(DiTingWebException):
    """Resource not found error."""

    def __init__(self, resource: str, resource_id: str) -> None:
        """Initialize exception."""
        message = f"{resource} not found: {resource_id}"
        super().__init__(message, code=404)


class ResourceConflictError(DiTingWebException):
    """Resource conflict error."""

    def __init__(self, message: str) -> None:
        """Initialize exception."""
        super().__init__(message, code=409)


class ValidationError(DiTingWebException):
    """Validation error."""

    def __init__(self, message: str) -> None:
        """Initialize exception."""
        super().__init__(message, code=400)


class BusinessError(DiTingWebException):
    """Business logic error."""

    def __init__(self, message: str, code: int = 400) -> None:
        """Initialize exception."""
        super().__init__(message, code=code)


class TaskError(DiTingWebException):
    """Task execution error."""

    def __init__(self, message: str) -> None:
        """Initialize exception."""
        super().__init__(message, code=500)

