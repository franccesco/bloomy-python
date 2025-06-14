"""Tests for the exceptions module."""

import pytest

from bloomy.exceptions import (
    APIError,
    AuthenticationError,
    BloomyError,
    ConfigurationError,
)


class TestExceptions:
    """Test cases for exception classes."""

    def test_bloomy_error(self):
        """Test base BloomyError exception."""
        with pytest.raises(BloomyError) as exc_info:
            raise BloomyError("Test error")

        assert str(exc_info.value) == "Test error"
        assert isinstance(exc_info.value, Exception)

    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Config error")

        assert str(exc_info.value) == "Config error"
        assert isinstance(exc_info.value, BloomyError)

    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Auth error")

        assert str(exc_info.value) == "Auth error"
        assert isinstance(exc_info.value, BloomyError)

    def test_api_error_with_status_code(self):
        """Test APIError exception with status code."""
        with pytest.raises(APIError) as exc_info:
            raise APIError("API error", status_code=404)

        assert str(exc_info.value) == "API error"
        assert exc_info.value.status_code == 404
        assert isinstance(exc_info.value, BloomyError)

    def test_api_error_without_status_code(self):
        """Test APIError exception without status code."""
        with pytest.raises(APIError) as exc_info:
            raise APIError("API error")

        assert str(exc_info.value) == "API error"
        assert exc_info.value.status_code is None

    def test_exception_hierarchy(self):
        """Test exception hierarchy."""
        # All custom exceptions should inherit from BloomyError
        assert issubclass(ConfigurationError, BloomyError)
        assert issubclass(AuthenticationError, BloomyError)
        assert issubclass(APIError, BloomyError)

        # BloomyError should inherit from Exception
        assert issubclass(BloomyError, Exception)
