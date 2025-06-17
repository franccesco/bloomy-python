"""Tests for abstract operations base classes."""


import pytest

from bloomy.utils.abstract_operations import AbstractOperations


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self) -> None:
        self.base_url = "https://app.bloomgrowth.com/api/v1"
        self.headers = {"Authorization": "Bearer test-token"}


class ConcreteOperations(AbstractOperations):
    """Concrete implementation for testing."""

    @property
    def user_id(self) -> int:
        """Get the current user's ID."""
        if self._user_id is None:
            self._user_id = 123
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        """Set the user ID."""
        self._user_id = value


class TestAbstractOperations:
    """Test cases for AbstractOperations."""

    def test_init(self) -> None:
        """Test initialization of abstract operations."""
        client = MockHTTPClient()
        ops = ConcreteOperations(client)

        assert ops._client == client
        assert ops._user_id is None

    def test_user_id_property(self) -> None:
        """Test user_id property getter and setter."""
        client = MockHTTPClient()
        ops = ConcreteOperations(client)

        # Test getter with default
        assert ops.user_id == 123
        assert ops._user_id == 123  # Should be cached

        # Test setter
        ops.user_id = 456
        assert ops.user_id == 456
        assert ops._user_id == 456

    def test_validate_mutual_exclusion(self) -> None:
        """Test mutual exclusion validation."""
        client = MockHTTPClient()
        ops = ConcreteOperations(client)

        # Should not raise when only one param is provided
        ops._validate_mutual_exclusion(1, None, "param1", "param2")
        ops._validate_mutual_exclusion(None, 2, "param1", "param2")
        ops._validate_mutual_exclusion(None, None, "param1", "param2")

        # Should raise when both params are provided
        with pytest.raises(ValueError, match="Cannot specify both param1 and param2"):
            ops._validate_mutual_exclusion(1, 2, "param1", "param2")

    def test_prepare_params(self) -> None:
        """Test prepare_params method."""
        client = MockHTTPClient()
        ops = ConcreteOperations(client)

        # Test with None values
        params = ops._prepare_params(a=1, b=None, c="test", d=None)
        assert params == {"a": 1, "c": "test"}

        # Test with no None values
        params = ops._prepare_params(x=1, y=2, z=3)
        assert params == {"x": 1, "y": 2, "z": 3}

        # Test with all None values
        params = ops._prepare_params(a=None, b=None)
        assert params == {}
