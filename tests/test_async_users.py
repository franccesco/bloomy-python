"""Tests for async user operations."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import UserDetails


class TestAsyncUserOperations:
    """Test cases for AsyncUserOperations."""

    @pytest.fixture
    def mock_async_client(self) -> AsyncMock:
        """Create a mock async HTTP client.

        Returns:
            A mock async HTTP client.

        """
        mock = AsyncMock()
        mock.headers = {"Authorization": "Bearer test-api-key"}
        return mock

    @pytest_asyncio.fixture
    async def async_client(self, mock_async_client: AsyncMock) -> AsyncClient:
        """Create an AsyncClient with mocked HTTP client.

        Returns:
            An AsyncClient instance with mocked HTTP client.

        """
        client = AsyncClient(api_key="test-api-key")
        await client.close()  # Close the real client
        client._client = mock_async_client  # type: ignore[assignment]
        # Also update the operations to use the mocked client
        client.user._client = mock_async_client  # type: ignore[assignment]
        client.meeting._client = mock_async_client  # type: ignore[assignment]
        client.todo._client = mock_async_client  # type: ignore[assignment]
        return client

    @pytest.mark.asyncio
    async def test_details_basic(
        self,
        async_client: AsyncClient,
        mock_async_client: AsyncMock,
        sample_user_data: dict[str, Any],
    ) -> None:
        """Test fetching basic user details."""
        # Mock the responses
        mock_response = MagicMock()
        mock_response.json.return_value = sample_user_data
        mock_response.raise_for_status = MagicMock()

        # Set up async mock to return the response
        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.user.details(user_id=123)

        # Verify the result
        assert isinstance(result, UserDetails)
        assert result.id == 123
        assert result.name == "John Doe"
        assert result.image_url == "https://example.com/avatar.jpg"
        assert result.direct_reports is None
        assert result.positions is None

        # Verify the API call
        mock_async_client.get.assert_called_once_with("users/123")

    @pytest.mark.asyncio
    async def test_search(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test searching for users."""
        # Mock the response data
        search_data = [
            {
                "Id": 123,
                "Name": "John Doe",
                "Description": "Software Engineer",
                "Email": "john.doe@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/john.jpg",
            },
            {
                "Id": 124,
                "Name": "John Smith",
                "Description": "Product Manager",
                "Email": "john.smith@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/smith.jpg",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = search_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.user.search("john")

        # Verify the result
        assert len(result) == 2
        assert result[0].name == "John Doe"
        assert result[1].name == "John Smith"

        # Verify the API call
        mock_async_client.get.assert_called_once_with(
            "search/user", params={"term": "john"}
        )
