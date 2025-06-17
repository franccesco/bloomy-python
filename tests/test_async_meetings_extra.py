"""Additional tests for async meeting operations to improve coverage."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.exceptions import APIError
from bloomy.models import Issue, Todo


class TestAsyncMeetingOperationsExtra:
    """Additional test cases for AsyncMeetingOperations."""

    @pytest.fixture
    def mock_async_client(self) -> AsyncMock:
        """Create a mock async HTTP client."""
        mock = AsyncMock()
        mock.headers = {"Authorization": "Bearer test-api-key"}
        return mock

    @pytest_asyncio.fixture
    async def async_client(self, mock_async_client: AsyncMock) -> AsyncClient:
        """Create an AsyncClient with mocked HTTP client."""
        client = AsyncClient(api_key="test-api-key")
        await client.close()  # Close the real client
        client._client = mock_async_client  # type: ignore[assignment]
        # Also update the operations to use the mocked client
        client.user._client = mock_async_client  # type: ignore[assignment]
        client.meeting._client = mock_async_client  # type: ignore[assignment]
        client.todo._client = mock_async_client  # type: ignore[assignment]
        return client

    @pytest.mark.asyncio
    async def test_issues(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting issues."""
        # Mock the response data
        issues_data = [
            {
                "Id": 1,
                "Name": "Issue 1",
                "DetailsUrl": "https://example.com/issue/1",
                "CreateDate": "2024-01-01T10:00:00Z",
                "MeetingId": 123,
                "MeetingName": "Weekly Meeting",
                "OwnerName": "John Doe",
                "OwnerId": 456,
                "OwnerImageUrl": "https://example.com/john.jpg",
                "ClosedDate": None,
                "CompletionDate": None,
            },
            {
                "Id": 2,
                "Name": "Issue 2",
                "DetailsUrl": "https://example.com/issue/2",
                "CreateDate": "2024-01-02T10:00:00Z",
                "MeetingId": 123,
                "MeetingName": "Weekly Meeting",
                "OwnerName": "Jane Smith",
                "OwnerId": 789,
                "OwnerImageUrl": "https://example.com/jane.jpg",
                "ClosedDate": "2024-01-03T10:00:00Z",
                "CompletionDate": "2024-01-03T10:00:00Z",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = issues_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.meeting.issues(123)

        # Verify the result
        assert len(result) == 2
        assert isinstance(result[0], Issue)
        assert result[0].id == 1
        assert result[0].name == "Issue 1"
        assert result[0].closed_date is None
        assert result[1].closed_date is not None

        # Verify the API call with correct parameters
        mock_async_client.get.assert_called_once_with(
            "L10/123/issues", params={"include_resolved": False}
        )

    @pytest.mark.asyncio
    async def test_issues_include_closed(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting issues including closed ones."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method with include_closed=True
        result = await async_client.meeting.issues(123, include_closed=True)

        # Verify the result
        assert result == []

        # Verify the API call with correct parameters
        mock_async_client.get.assert_called_once_with(
            "L10/123/issues", params={"include_resolved": True}
        )

    @pytest.mark.asyncio
    async def test_todos(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting todos."""
        # Mock the response data
        todos_data = [
            {
                "Id": 1,
                "Name": "Todo 1",
                "DetailsUrl": "https://example.com/todo/1",
                "DueDate": "2024-01-08T10:00:00Z",
                "CompleteTime": None,
                "CreateTime": "2024-01-01T10:00:00Z",
                "OriginId": 123,
                "Origin": "Weekly Meeting",
                "Complete": False,
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = todos_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.meeting.todos(123)

        # Verify the result
        assert len(result) == 1
        assert isinstance(result[0], Todo)
        assert result[0].id == 1

        # Verify the API call with correct parameters
        mock_async_client.get.assert_called_once_with(
            "L10/123/todos", params={"INCLUDE_CLOSED": False}
        )

    @pytest.mark.asyncio
    async def test_todos_include_closed(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting todos including closed ones."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method with include_closed=True
        result = await async_client.meeting.todos(123, include_closed=True)

        # Verify the result
        assert result == []

        # Verify the API call with correct parameters
        mock_async_client.get.assert_called_once_with(
            "L10/123/todos", params={"INCLUDE_CLOSED": True}
        )

    @pytest.mark.asyncio
    async def test_details_meeting_not_found(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test details when meeting is not found."""
        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock empty meetings list
        mock_meetings_response = MagicMock()
        mock_meetings_response.json.return_value = []
        mock_meetings_response.raise_for_status = MagicMock()

        def get_side_effect(url: str) -> MagicMock:
            if url == "users/mine":
                return mock_user_response
            elif url == "L10/456/list":
                return mock_meetings_response
            else:
                raise ValueError(f"Unexpected URL: {url}")

        mock_async_client.get.side_effect = get_side_effect

        # Call the method and expect error
        with pytest.raises(APIError, match="Meeting with ID 999 not found"):
            await async_client.meeting.details(999)
