"""Tests for async meeting operations."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import MeetingDetails


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
        # Mock the user ID for operations
        client.meeting._user_id = 456
        return client

    @pytest.mark.asyncio
    async def test_create_many_all_successful(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where all meetings are created successfully."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock create responses for each meeting
        created_meetings = [
            {
                "meetingId": 100,
            },
            {
                "meetingId": 101,
            },
            {
                "meetingId": 102,
            },
        ]

        # Create mock responses for each meeting
        mock_create_responses = []
        for meeting_data in created_meetings:
            mock_response = MagicMock()
            mock_response.json.return_value = meeting_data
            mock_response.raise_for_status = MagicMock()
            mock_create_responses.append(mock_response)

        # Mock response for adding attendee (for meeting with attendees)
        mock_attendee_response = MagicMock()
        mock_attendee_response.raise_for_status = MagicMock()
        mock_create_responses.append(mock_attendee_response)

        # Set up side effects
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.side_effect = mock_create_responses

        # Test data
        meetings_to_create = [
            {"title": "Weekly Standup"},
            {"title": "Sprint Planning", "attendees": [789]},
            {"title": "Retrospective", "add_self": True},
        ]

        # Call the method
        result = await async_client.meeting.create_many(meetings_to_create)

        # Verify the result
        assert len(result.successful) == 3
        assert len(result.failed) == 0
        assert all(isinstance(meeting, dict) for meeting in result.successful)
        assert result.successful[0]["meeting_id"] == 100
        assert result.successful[0]["title"] == "Weekly Standup"
        assert result.successful[0]["attendees"] == []
        assert result.successful[1]["meeting_id"] == 101
        assert result.successful[1]["title"] == "Sprint Planning"
        assert result.successful[1]["attendees"] == [789]
        assert result.successful[2]["meeting_id"] == 102
        assert result.successful[2]["title"] == "Retrospective"
        assert result.successful[2]["attendees"] == []

        # Verify API calls
        assert mock_async_client.post.call_count == 4  # 3 meetings + 1 attendee add

    @pytest.mark.asyncio
    async def test_create_many_partial_failure(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where some meetings fail."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock responses - 1st succeeds, 2nd fails with 400, 3rd fails with 500
        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {
            "meetingId": 200,
        }
        mock_success_response.raise_for_status = MagicMock()

        # Create error responses
        from httpx import HTTPStatusError, Response

        mock_400_response = Response(400, json={"error": "Bad Request"})
        mock_400_error = HTTPStatusError(
            "Bad Request", request=None, response=mock_400_response
        )

        mock_500_response = Response(500, json={"error": "Internal Server Error"})
        mock_500_error = HTTPStatusError(
            "Internal Server Error", request=None, response=mock_500_response
        )

        # Set up side effects
        mock_async_client.get.return_value = mock_user_response

        # Create side effect function that tracks call count
        call_count = 0

        def post_side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_success_response
            elif call_count == 2:
                # For 400 error, raise_for_status will throw
                mock_resp = MagicMock()
                mock_resp.raise_for_status.side_effect = mock_400_error
                return mock_resp
            else:
                # For 500 error, raise_for_status will throw
                mock_resp = MagicMock()
                mock_resp.raise_for_status.side_effect = mock_500_error
                return mock_resp

        mock_async_client.post.side_effect = post_side_effect

        # Test data
        meetings_to_create = [
            {"title": "Success Meeting"},
            {"title": "Bad Request Meeting"},
            {"title": "Server Error Meeting"},
        ]

        # Call the method
        result = await async_client.meeting.create_many(meetings_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.successful[0]["meeting_id"] == 200
        assert result.successful[0]["title"] == "Success Meeting"
        assert result.successful[0]["attendees"] == []

        # Check failed items
        assert result.failed[0].index == 1
        assert result.failed[0].input_data == meetings_to_create[1]
        assert "Bad Request" in result.failed[0].error

        assert result.failed[1].index == 2
        assert result.failed[1].input_data == meetings_to_create[2]
        assert "Internal Server Error" in result.failed[1].error

    @pytest.mark.asyncio
    async def test_create_many_empty_list(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with an empty list."""
        # Call the method with empty list
        result = await async_client.meeting.create_many([])

        # Verify the result
        assert len(result.successful) == 0
        assert len(result.failed) == 0

        # Verify no API calls were made
        mock_async_client.get.assert_not_called()
        mock_async_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_many_validation_errors(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with validation errors (missing required fields)."""
        # Test data with missing required fields
        meetings_to_create = [
            {"title": "Valid Meeting"},  # Valid
            {},  # Missing title
            {"attendees": [123]},  # Missing title
        ]

        # Mock user ID response for valid meeting
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock successful create response for valid meeting
        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {
            "meetingId": 300,
        }
        mock_create_response.raise_for_status = MagicMock()

        # Set up mocks
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.return_value = mock_create_response

        # Call the method
        result = await async_client.meeting.create_many(meetings_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.successful[0]["meeting_id"] == 300
        assert result.successful[0]["title"] == "Valid Meeting"
        assert result.successful[0]["attendees"] == []

        # Check validation errors
        assert result.failed[0].index == 1
        assert "title is required" in result.failed[0].error

        assert result.failed[1].index == 2
        assert "title is required" in result.failed[1].error

        # Only one successful creation should have been attempted
        assert mock_async_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_create_many_concurrent_execution(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test that create_many executes operations concurrently."""
        import time

        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Track when each call starts and ends
        call_times = []

        async def delayed_post(*_args, **_kwargs):
            """Simulate a network call with delay.

            Returns:
                Mock response object.

            """
            start_time = time.time()
            await asyncio.sleep(0.1)  # Simulate network delay
            end_time = time.time()
            call_times.append((start_time, end_time))

            # Return a mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "meetingId": len(call_times) + 400,
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        # Set up mocks
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.side_effect = delayed_post

        # Create multiple meetings
        meetings_to_create = [{"title": f"Meeting {i}"} for i in range(5)]

        # Call the method with max_concurrent=3
        start_time = time.time()
        result = await async_client.meeting.create_many(
            meetings_to_create, max_concurrent=3
        )
        total_time = time.time() - start_time

        # Verify all were successful
        assert len(result.successful) == 5
        assert len(result.failed) == 0

        # Verify concurrent execution
        # With max_concurrent=3 and 5 meetings with 0.1s delay each:
        # - First 3 should start almost simultaneously
        # - Next 2 should start after first ones complete
        # Total time should be ~0.2s (2 batches) not ~0.5s (sequential)
        assert total_time < 0.3  # Allow some overhead

        # Check that we had overlapping executions
        overlapping_count = 0
        for i in range(len(call_times) - 1):
            for j in range(i + 1, len(call_times)):
                # Check if execution times overlap
                if (
                    call_times[i][0] < call_times[j][1]
                    and call_times[j][0] < call_times[i][1]
                ):
                    overlapping_count += 1

        assert overlapping_count > 0  # Confirm concurrent execution

    @pytest.mark.asyncio
    async def test_get_many_all_successful(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk retrieval where all meetings are retrieved successfully."""
        # Mock meeting list response for details method
        mock_meetings_list = [
            {"Id": 100, "Type": "L10", "Key": "L10-100", "Name": "Weekly Standup"},
            {"Id": 101, "Type": "L10", "Key": "L10-101", "Name": "Sprint Planning"},
            {"Id": 102, "Type": "L10", "Key": "L10-102", "Name": "Retrospective"},
        ]

        # Mock attendees responses
        attendees_responses = {
            100: [
                {
                    "UserId": 456,
                    "Name": "John Doe",
                    "ImageUrl": "https://example.com/img1.jpg",
                }
            ],
            101: [
                {
                    "UserId": 456,
                    "Name": "John Doe",
                    "ImageUrl": "https://example.com/img1.jpg",
                },
                {
                    "UserId": 789,
                    "Name": "Jane Smith",
                    "ImageUrl": "https://example.com/img2.jpg",
                },
            ],
            102: [
                {
                    "UserId": 456,
                    "Name": "John Doe",
                    "ImageUrl": "https://example.com/img1.jpg",
                }
            ],
        }

        # Create side effect function that returns appropriate response based on URL
        def get_side_effect(url, **_kwargs):
            mock_response = MagicMock()

            if url.endswith("/list"):
                mock_response.json.return_value = mock_meetings_list
            elif "/attendees" in url:
                # Extract meeting ID from URL
                meeting_id = int(url.split("/")[1])
                mock_response.json.return_value = attendees_responses.get(
                    meeting_id, []
                )
            else:
                # For issues, todos, metrics
                mock_response.json.return_value = []

            mock_response.raise_for_status = MagicMock()
            return mock_response

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        meeting_ids = [100, 101, 102]
        result = await async_client.meeting.get_many(meeting_ids)

        # Verify the result
        assert len(result.successful) == 3
        assert len(result.failed) == 0
        assert all(isinstance(meeting, MeetingDetails) for meeting in result.successful)
        assert result.successful[0].id == 100
        assert result.successful[0].name == "Weekly Standup"
        assert len(result.successful[0].attendees) == 1
        assert result.successful[1].id == 101
        assert result.successful[1].name == "Sprint Planning"
        assert len(result.successful[1].attendees) == 2
        assert result.successful[2].id == 102
        assert result.successful[2].name == "Retrospective"
        assert len(result.successful[2].attendees) == 1

        # Verify API calls - 5 calls per meeting
        # (list, attendees, issues, todos, metrics)
        assert mock_async_client.get.call_count == 15

    @pytest.mark.asyncio
    async def test_get_many_partial_failure(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk retrieval where some meetings fail."""
        # Mock meeting list response - contains meeting 200 but not 999 or 500
        mock_meetings_list = [
            {"Id": 200, "Type": "L10", "Key": "L10-200", "Name": "Success Meeting"},
        ]

        # Create side effect function that returns appropriate response based on URL
        def get_side_effect(url, **_kwargs):
            mock_response = MagicMock()

            if url.endswith("/list"):
                mock_response.json.return_value = mock_meetings_list
            elif "/200/attendees" in url:
                mock_response.json.return_value = [
                    {
                        "UserId": 456,
                        "Name": "John Doe",
                        "ImageUrl": "https://example.com/img1.jpg",
                    }
                ]
            else:
                # For issues, todos, metrics
                mock_response.json.return_value = []

            mock_response.raise_for_status = MagicMock()
            return mock_response

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        meeting_ids = [200, 999, 500]
        result = await async_client.meeting.get_many(meeting_ids)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.successful[0].id == 200
        assert result.successful[0].name == "Success Meeting"

        # Check failed items
        assert result.failed[0].index == 1
        assert result.failed[0].input_data["meeting_id"] == 999
        assert "not found" in result.failed[0].error.lower()

        assert result.failed[1].index == 2
        assert result.failed[1].input_data["meeting_id"] == 500
        assert "not found" in result.failed[1].error.lower()

    @pytest.mark.asyncio
    async def test_get_many_empty_list(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk retrieval with an empty list."""
        # Call the method with empty list
        result = await async_client.meeting.get_many([])

        # Verify the result
        assert len(result.successful) == 0
        assert len(result.failed) == 0

        # Verify no API calls were made
        mock_async_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_many_concurrent_execution(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test that get_many executes operations concurrently."""
        import time

        # Track when each call starts and ends
        call_times = []

        async def delayed_get(*args, **_kwargs):
            """Simulate a network call with delay.

            Returns:
                Mock response object.

            """
            start_time = time.time()
            await asyncio.sleep(0.1)  # Simulate network delay
            end_time = time.time()
            call_times.append((start_time, end_time))

            # Return mock responses based on URL pattern
            mock_response = MagicMock()

            # Extract the URL from args (first positional argument)
            url = args[0] if args else ""

            if url.endswith("/list"):
                # Return list of all meetings
                mock_response.json.return_value = [
                    {
                        "Id": i + 400,
                        "Type": "L10",
                        "Key": f"L10-{i + 400}",
                        "Name": f"Meeting {i}",
                    }
                    for i in range(5)
                ]
            elif "/attendees" in url:
                # Return attendees for any meeting
                mock_response.json.return_value = [
                    {
                        "UserId": 456,
                        "Name": "John Doe",
                        "ImageUrl": "https://example.com/img.jpg",
                    }
                ]
            else:
                # For issues, todos, metrics
                mock_response.json.return_value = []

            mock_response.raise_for_status = MagicMock()
            return mock_response

        # Set up mocks
        mock_async_client.get.side_effect = delayed_get

        # Get multiple meetings
        meeting_ids = list(range(400, 405))

        # Call the method with max_concurrent=3
        start_time = time.time()
        result = await async_client.meeting.get_many(meeting_ids, max_concurrent=3)
        total_time = time.time() - start_time

        # Verify all were successful
        assert len(result.successful) == 5
        assert len(result.failed) == 0

        # Verify concurrent execution
        # With max_concurrent=3 and 5 meetings:
        # Each meeting makes 5 API calls (list, attendees, issues, todos, metrics)
        # Each call has 0.1s delay, so each meeting takes ~0.5s
        # With concurrency of 3, we should see significant speedup vs sequential
        # Sequential would take 5 * 0.5 = 2.5s
        # Concurrent should be much faster
        assert total_time < 1.5  # Should be much faster than sequential

        # Verify we made all the expected API calls
        # 5 meetings * 5 calls per meeting = 25 total calls
        assert len(call_times) == 25

        # Check that we had overlapping executions by looking at concurrent calls
        # Count how many calls were running at the same time
        max_concurrent_calls = 0
        for i, (start_i, end_i) in enumerate(call_times):
            concurrent = 1  # Count self
            for j, (start_j, end_j) in enumerate(call_times):
                if i != j and start_i < end_j and start_j < end_i:
                    concurrent += 1
            max_concurrent_calls = max(max_concurrent_calls, concurrent)

        # With max_concurrent=3, we should see at least 3 calls running concurrently
        assert max_concurrent_calls >= 3
