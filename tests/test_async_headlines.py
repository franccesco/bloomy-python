"""Tests for async headline operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import HeadlineDetails, HeadlineInfo, HeadlineListItem


class TestAsyncHeadlineOperations:
    """Test async headline operations."""

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
        client.headline._client = mock_async_client  # type: ignore[assignment]
        # Mock the user ID for operations
        client.headline._user_id = 1
        return client

    @pytest.mark.asyncio
    async def test_create(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test creating a new headline."""
        mock_response_data = {
            "Id": 501,
            "Name": "Product launch successful",
            "DetailsUrl": "https://example.com/headline/501",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_response

        headline = await async_client.headline.create(
            meeting_id=10,
            title="Product launch successful",
            notes="Exceeded targets by 15%",
        )

        assert isinstance(headline, HeadlineInfo)
        assert headline.id == 501
        assert headline.title == "Product launch successful"
        assert headline.owner_details.id == 1

        mock_async_client.post.assert_called_once_with(
            "L10/10/headlines",
            json={
                "title": "Product launch successful",
                "ownerId": 1,
                "notes": "Exceeded targets by 15%",
            },
        )

    @pytest.mark.asyncio
    async def test_update(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test updating a headline."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.put.return_value = mock_response

        result = await async_client.headline.update(
            headline_id=501, title="Updated headline"
        )

        assert result is None
        mock_async_client.put.assert_called_once_with(
            "headline/501", json={"title": "Updated headline"}
        )

    @pytest.mark.asyncio
    async def test_details(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test getting headline details."""
        mock_data = {
            "Id": 501,
            "Name": "Product launch successful",
            "DetailsUrl": "https://example.com/headline/501",
            "OriginId": 456,
            "Origin": "Product Meeting",
            "Owner": {"Id": 123, "Name": "John Doe"},
            "Archived": False,
            "CreateTime": "2024-06-01T10:00:00Z",
            "CloseTime": None,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        headline = await async_client.headline.details(501)

        assert isinstance(headline, HeadlineDetails)
        assert headline.id == 501
        assert headline.title == "Product launch successful"
        assert headline.meeting_details.id == 456
        assert headline.owner_details.name == "John Doe"
        assert headline.archived is False

        mock_async_client.get.assert_called_once_with(
            "headline/501", params={"Include_Origin": "true"}
        )

    @pytest.mark.asyncio
    async def test_list_by_user(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing headlines by user."""
        mock_data = [
            {
                "Id": 501,
                "Name": "First headline",
                "OriginId": 456,
                "Origin": "Product Meeting",
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Archived": False,
                "CreateTime": "2024-06-01T10:00:00Z",
                "CloseTime": None,
            },
            {
                "Id": 502,
                "Name": "Second headline",
                "OriginId": 457,
                "Origin": "Team Meeting",
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Archived": True,
                "CreateTime": "2024-05-01T10:00:00Z",
                "CloseTime": "2024-05-15T10:00:00Z",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        headlines = await async_client.headline.list()

        assert len(headlines) == 2
        assert isinstance(headlines[0], HeadlineListItem)
        assert headlines[0].id == 501
        assert headlines[0].title == "First headline"
        assert headlines[1].archived is True

        mock_async_client.get.assert_called_once_with("headline/users/1")

    @pytest.mark.asyncio
    async def test_list_by_meeting(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing headlines by meeting."""
        mock_data = [
            {
                "Id": 501,
                "Name": "Meeting headline",
                "OriginId": 456,
                "Origin": "Product Meeting",
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Archived": False,
                "CreateTime": "2024-06-01T10:00:00Z",
                "CloseTime": None,
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        headlines = await async_client.headline.list(meeting_id=456)

        assert len(headlines) == 1
        assert headlines[0].title == "Meeting headline"

        mock_async_client.get.assert_called_once_with("l10/456/headlines")

    @pytest.mark.asyncio
    async def test_list_invalid_params(self, async_client: AsyncClient):
        """Test listing headlines with both user_id and meeting_id raises error."""
        with pytest.raises(
            ValueError, match="Please provide either user_id or meeting_id"
        ):
            await async_client.headline.list(user_id=1, meeting_id=456)

    @pytest.mark.asyncio
    async def test_delete(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test deleting a headline."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.delete.return_value = mock_response

        result = await async_client.headline.delete(501)

        assert result is None
        mock_async_client.delete.assert_called_once_with("headline/501")
