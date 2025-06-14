"""Exceptions for the Bloomy SDK."""


class BloomyError(Exception):
    """Base exception for all Bloomy-related errors."""

    pass


class ConfigurationError(BloomyError):
    """Raised when there's an issue with configuration."""

    pass


class AuthenticationError(BloomyError):
    """Raised when authentication fails."""

    pass


class APIError(BloomyError):
    """Raised when API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
