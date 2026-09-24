"""Exceptions for the Bloomy SDK."""

from __future__ import annotations

from typing import Any


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
        """Initialize API error with message and optional status code.

        Args:
            message: The error message
            status_code: The HTTP status code if available

        """
        super().__init__(message)
        self.status_code = status_code


class GraphQLError(APIError):
    """Raised when the v2 GraphQL API returns an error.

    This covers three cases, all surfaced identically to callers:
    a response body with a top-level `errors` array (whether it came back
    with an HTTP 4xx validation status or a 200 execution status), and a
    mutation result shaped like `{success message errorDetails{message}}`
    where `success` is `false`.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize a GraphQL error with message, status code, and raw errors.

        Args:
            message: The error message.
            status_code: The HTTP status code if available.
            errors: The raw GraphQL `errors` array (or synthesized `errorDetails`
                entries for failed mutation results), if available.

        """
        super().__init__(message, status_code=status_code)
        self.errors: list[dict[str, Any]] = errors or []
