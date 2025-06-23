"""Tests for async base operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bloomy.utils.async_base_operations import AsyncBaseOperations


class MockAsyncHTTPClient:
    """Mock async HTTP client for testing."""

    def __init__(self) -> None:
        """Initialize mock async HTTP client with base URL and headers."""
        self.base_url = "https://app.bloomgrowth.com/api/v1"
        self.headers = {"Authorization": "Bearer test-token"}
        self.get = AsyncMock()


class TestAsyncBaseOperations:
    """Test cases for AsyncBaseOperations."""

    @pytest.mark.asyncio
    async def test_user_id_property_default(self) -> None:
        """Test async user_id property with default fetch."""
        client = MockAsyncHTTPClient()

        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"Id": 789}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        ops = AsyncBaseOperations(client)

        # First access should fetch from API
        user_id = await ops.get_user_id()
        assert user_id == 789
        assert ops._user_id == 789

        # Second access should use cached value
        client.get.reset_mock()
        user_id2 = await ops.get_user_id()
        assert user_id2 == 789
        client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_id_property_setter(self) -> None:
        """Test setting user_id property."""
        client = MockAsyncHTTPClient()
        ops = AsyncBaseOperations(client)

        # Set user ID directly
        ops.user_id = 999
        assert ops._user_id == 999

        # Should use set value, not fetch from API
        user_id = await ops.get_user_id()
        assert user_id == 999
        client.get.assert_not_called()

        # Also test property access
        assert ops.user_id == 999

    @pytest.mark.asyncio
    async def test_get_default_user_id(self) -> None:
        """Test _get_default_user_id method."""
        client = MockAsyncHTTPClient()

        # Mock the API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"Id": 555}
        mock_response.raise_for_status = MagicMock()
        client.get.return_value = mock_response

        ops = AsyncBaseOperations(client)

        # Call the protected method directly
        user_id = await ops._get_default_user_id()
        assert user_id == 555

        # Verify API call
        client.get.assert_called_once_with("users/mine")
