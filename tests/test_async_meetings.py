"""Tests for async meeting operations."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import (
    MeetingAttendee,
    MeetingDetails,
    MeetingListItem,
    ScorecardMetric,
)


class TestAsyncMeetingOperations:
    """Test cases for AsyncMeetingOperations."""

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
    async def test_list(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test listing meetings."""
        # Mock the response data
        meeting_data = [
            {
                "Id": 123,
                "Type": "L10",
                "Key": "L10-123",
                "Name": "Weekly Team Meeting",
            },
            {
                "Id": 124,
                "Type": "L10",
                "Key": "L10-124",
                "Name": "Project Review",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = meeting_data
        mock_response.raise_for_status = MagicMock()

        # Set up mock to return user response first, then meetings
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        def get_side_effect(url: str) -> MagicMock:
            if url == "users/mine":
                return mock_user_response
            elif url == "L10/456/list":
                return mock_response
            else:
                raise ValueError(f"Unexpected URL: {url}")

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        result = await async_client.meeting.list()

        # Verify the result
        assert len(result) == 2
        assert isinstance(result[0], MeetingListItem)
        assert result[0].id == 123
        assert result[0].name == "Weekly Team Meeting"
        assert result[1].id == 124
        assert result[1].name == "Project Review"

        # Verify the API calls
        assert mock_async_client.get.call_count == 2
        mock_async_client.get.assert_any_call("users/mine")
        mock_async_client.get.assert_any_call("L10/456/list")

    @pytest.mark.asyncio
    async def test_attendees(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting attendees."""
        # Mock the response data
        attendee_data = [
            {
                "UserId": 1,
                "Name": "John Doe",
                "ImageUrl": "https://example.com/john.jpg",
            },
            {
                "UserId": 2,
                "Name": "Jane Smith",
                "ImageUrl": "https://example.com/jane.jpg",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = attendee_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.meeting.attendees(123)

        # Verify the result
        assert len(result) == 2
        assert isinstance(result[0], MeetingAttendee)
        assert result[0].user_id == 1
        assert result[0].name == "John Doe"
        assert result[0].image_url == "https://example.com/john.jpg"

        # Verify the API call
        mock_async_client.get.assert_called_once_with("L10/123/attendees")

    @pytest.mark.asyncio
    async def test_metrics(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting metrics."""
        # Mock the response data
        metrics_data = [
            {
                "Id": 1,
                "Name": "Revenue",
                "Target": 100000,
                "Modifiers": "$",
                "Direction": ">",
                "Owner": {"Id": 123, "Name": "John Doe"},
            },
            {
                "Id": 2,
                "Name": "Customer Satisfaction",
                "Target": 90,
                "Modifiers": "%",
                "Direction": ">",
                "Owner": {"Id": 124, "Name": "Jane Smith"},
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = metrics_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.meeting.metrics(123)

        # Verify the result
        assert len(result) == 2
        assert isinstance(result[0], ScorecardMetric)
        assert result[0].id == 1
        assert result[0].title == "Revenue"
        assert result[0].target == 100000.0
        assert result[0].unit == "$"

        # Verify the API call
        mock_async_client.get.assert_called_once_with("L10/123/measurables")

    @pytest.mark.asyncio
    async def test_create(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test creating a meeting."""
        # Mock the response data
        created_meeting = {
            "meetingId": 125,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = created_meeting
        mock_response.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_response

        # Mock user ID
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()
        mock_async_client.get.return_value = mock_user_response

        # Call the method
        result = await async_client.meeting.create(
            title="New Meeting",
            attendees=[1, 2, 3],
        )

        # Verify the result
        assert isinstance(result, dict)
        assert result["meeting_id"] == 125
        assert result["title"] == "New Meeting"
        assert result["attendees"] == [1, 2, 3]

        # Verify the API calls
        # Should be 4 posts: 1 for create + 3 for attendees
        assert mock_async_client.post.call_count == 4

        # Check the create call
        create_call = mock_async_client.post.call_args_list[0]
        assert create_call[0][0] == "L10/create"
        payload = create_call[1]["json"]
        assert payload["title"] == "New Meeting"
        assert payload["addSelf"] is True

    @pytest.mark.asyncio
    async def test_delete(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test deleting a meeting."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_async_client.delete.return_value = mock_response

        # Call the method
        result = await async_client.meeting.delete(123)

        # Verify the result
        assert result is True

        # Verify the API call
        mock_async_client.delete.assert_called_once_with("L10/123")

    @pytest.mark.asyncio
    async def test_details(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test fetching meeting details with concurrent requests."""
        # Mock the base meeting response
        meeting_data = {
            "Id": 123,
            "Name": "Weekly Team Meeting",
            "Notes": "https://example.com/meeting/123",
            "CreateTime": "2024-01-01T10:00:00Z",
            "StartTime": None,
            "LeadingUserId": 456,
        }

        # Mock attendees response
        attendees_data = [
            {"UserId": 1, "Name": "John Doe", "ImageUrl": "https://example.com/john.jpg"}
        ]

        # Mock issues response
        issues_data = [
            {
                "Id": 1,
                "Name": "Issue 1",
                "DetailsUrl": "https://example.com/issue/1",
                "CreateDate": "2024-01-01T10:00:00Z",
                "MeetingId": 123,
                "MeetingName": "Weekly Team Meeting",
                "OwnerName": "John Doe",
                "OwnerId": 1,
                "OwnerImageUrl": "https://example.com/john.jpg",
                "ClosedDate": None,
                "CompletionDate": None,
            }
        ]

        # Mock todos response
        todos_data = [
            {
                "Id": 1,
                "Name": "Todo 1",
                "DetailsUrl": "https://example.com/todo/1",
                "DueDate": "2024-01-08T10:00:00Z",
                "CompleteTime": None,
                "CreateTime": "2024-01-01T10:00:00Z",
                "OriginId": 123,
                "Origin": "Weekly Team Meeting",
                "Complete": False,
            }
        ]

        # Mock metrics response
        metrics_data = [
            {
                "Id": 1,
                "Name": "Revenue",
                "Target": 100000,
                "Modifiers": "$",
                "Direction": ">",
                "Owner": {"Id": 123, "Name": "John Doe"},
            }
        ]

        # Create response mocks
        def create_response(data: Any) -> MagicMock:
            mock = MagicMock()
            mock.json.return_value = data
            mock.raise_for_status = MagicMock()
            return mock

        # Set up the mock to return different responses based on the URL
        def get_side_effect(url: str, **_kwargs: Any) -> MagicMock:
            if url == "users/mine":
                return create_response({"Id": 456})
            elif url == "L10/456/list":
                # Return a list containing the meeting we're looking for
                return create_response([{
                    "Id": 123,
                    "Type": "L10",
                    "Key": "L10-123",
                    "Name": "Weekly Team Meeting",
                }])
            elif url == "L10/123":
                return create_response(meeting_data)
            elif url == "L10/123/attendees":
                return create_response(attendees_data)
            elif url == "L10/123/issues":
                return create_response(issues_data)
            elif url == "L10/123/todos":
                return create_response(todos_data)
            elif url == "L10/123/measurables":
                return create_response(metrics_data)
            else:
                raise ValueError(f"Unexpected URL: {url}")

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        result = await async_client.meeting.details(123, include_closed=True)

        # Verify the result
        assert isinstance(result, MeetingDetails)
        assert result.id == 123
        assert result.name == "Weekly Team Meeting"
        assert len(result.attendees) == 1
        assert result.attendees[0].name == "John Doe"
        assert len(result.issues) == 1
        assert result.issues[0].name == "Issue 1"
        assert len(result.todos) == 1
        assert result.todos[0].name == "Todo 1"
        assert len(result.metrics) == 1
        assert result.metrics[0].title == "Revenue"

        # Verify all API calls were made
        # users/mine + L10/456/list + 4 sub-resources
        assert mock_async_client.get.call_count == 6
