"""Tests for async goal operations."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import ArchivedGoalInfo, CreatedGoalInfo, GoalInfo, GoalListResponse


class TestAsyncGoalOperations:
    """Test async goal operations."""

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
        client.goal._client = mock_async_client  # type: ignore[assignment]
        # Mock the user ID for operations
        client.goal._user_id = 1
        return client

    @pytest.mark.asyncio
    async def test_list_basic(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing goals for a user."""
        mock_data = [
            {
                "Id": 123,
                "Owner": {"Id": 1, "Name": "John Doe"},
                "Name": "Complete Project",
                "CreateTime": "2024-01-01",
                "DueDate": "2024-06-01",
                "Complete": False,
                "Origins": [{"Id": 10, "Name": "Team Meeting"}],
            },
            {
                "Id": 124,
                "Owner": {"Id": 1, "Name": "John Doe"},
                "Name": "Launch Feature",
                "CreateTime": "2024-01-02",
                "DueDate": "2024-07-01",
                "Complete": True,
                "Origins": [],
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        goals = await async_client.goal.list()

        assert len(goals) == 2
        assert isinstance(goals[0], GoalInfo)
        assert goals[0].id == 123
        assert goals[0].title == "Complete Project"
        assert goals[0].status == "Incomplete"
        assert goals[0].meeting_id == 10
        assert goals[1].status == "Completed"
        assert goals[1].meeting_id is None

        mock_async_client.get.assert_called_once_with(
            "rocks/user/1", params={"include_origin": True}
        )

    @pytest.mark.asyncio
    async def test_list_with_archived(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing goals with archived included."""
        active_data = [
            {
                "Id": 123,
                "Owner": {"Id": 1, "Name": "John Doe"},
                "Name": "Active Goal",
                "CreateTime": "2024-01-01",
                "DueDate": "2024-06-01",
                "Complete": False,
                "Origins": [],
            }
        ]

        archived_data = [
            {
                "Id": 125,
                "Name": "Archived Goal",
                "CreateTime": "2023-01-01",
                "DueDate": "2023-06-01",
                "Complete": True,
            }
        ]

        # Create separate mock responses for each call
        mock_response1 = MagicMock()
        mock_response1.json.return_value = active_data
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.json.return_value = archived_data
        mock_response2.raise_for_status = MagicMock()

        mock_async_client.get.side_effect = [mock_response1, mock_response2]

        result = await async_client.goal.list(archived=True)

        assert isinstance(result, GoalListResponse)
        assert len(result.active) == 1
        assert len(result.archived) == 1
        assert isinstance(result.active[0], GoalInfo)
        assert isinstance(result.archived[0], ArchivedGoalInfo)
        assert result.archived[0].id == 125
        assert result.archived[0].title == "Archived Goal"

    @pytest.mark.asyncio
    async def test_create(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test creating a new goal."""
        mock_response = {
            "Id": 126,
            "Owner": {"Id": 1, "Name": "John Doe"},
            "CreateTime": "2024-01-03",
            "Completion": 1,
            "Origins": [{"Id": 10, "Name": "Team Meeting"}],
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_resp

        goal = await async_client.goal.create(title="New Goal", meeting_id=10)

        assert isinstance(goal, CreatedGoalInfo)
        assert goal.id == 126
        assert goal.title == "New Goal"
        assert goal.status == "on"
        assert goal.meeting_id == 10

        mock_async_client.post.assert_called_once_with(
            "L10/10/rocks", json={"title": "New Goal", "accountableUserId": 1}
        )

    @pytest.mark.asyncio
    async def test_delete(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test deleting a goal."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.delete.return_value = mock_response

        result = await async_client.goal.delete(123)

        assert result is None
        mock_async_client.delete.assert_called_once_with("rocks/123")

    @pytest.mark.asyncio
    async def test_update(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test updating a goal."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.put.return_value = mock_response

        result = await async_client.goal.update(
            goal_id=123, title="Updated Goal", status="on"
        )

        assert result is None
        mock_async_client.put.assert_called_once_with(
            "rocks/123",
            json={
                "accountableUserId": 1,
                "title": "Updated Goal",
                "completion": "OnTrack",
            },
        )

    @pytest.mark.asyncio
    async def test_update_invalid_status(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test updating a goal with invalid status."""
        with pytest.raises(ValueError, match="Invalid status value"):
            await async_client.goal.update(goal_id=123, status="invalid")

    @pytest.mark.asyncio
    async def test_archive(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test archiving a goal."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.put.return_value = mock_response

        result = await async_client.goal.archive(123)

        assert result is None
        mock_async_client.put.assert_called_once_with("rocks/123/archive")

    @pytest.mark.asyncio
    async def test_restore(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test restoring an archived goal."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.put.return_value = mock_response

        result = await async_client.goal.restore(123)

        assert result is None
        mock_async_client.put.assert_called_once_with("rocks/123/restore")

    @pytest.mark.asyncio
    async def test_create_many_all_successful(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where all goals are created successfully."""
        # Mock user ID already set in fixture to 1

        # Mock create responses for each goal
        created_goals = [
            {
                "Id": 100,
                "Name": "Q1 Revenue Target",
                "AccountableUserId": 1,
                "AccountableUserInitials": "JD",
                "AccountableUserName": "John Doe",
                "DueDate": "2024-03-31T00:00:00Z",
                "Owner": {"Id": 1, "Name": "John Doe"},
                "CreateTime": "2024-01-01T10:00:00Z",
                "Completion": 1,  # Maps to "on" status
                "Origins": [{"Id": 125, "Name": "Team Meeting"}],
            },
            {
                "Id": 101,
                "Name": "Product Launch",
                "AccountableUserId": 789,
                "AccountableUserInitials": "JS",
                "AccountableUserName": "Jane Smith",
                "DueDate": "2024-06-30T00:00:00Z",
                "Owner": {"Id": 789, "Name": "Jane Smith"},
                "CreateTime": "2024-01-02T10:00:00Z",
                "Completion": 0,  # Maps to "off" status
                "Origins": [{"Id": 125, "Name": "Team Meeting"}],
            },
            {
                "Id": 102,
                "Name": "Team Expansion",
                "AccountableUserId": 1,
                "AccountableUserInitials": "JD",
                "AccountableUserName": "John Doe",
                "DueDate": "2024-12-31T00:00:00Z",
                "Owner": {"Id": 1, "Name": "John Doe"},
                "CreateTime": "2024-01-03T10:00:00Z",
                "Completion": 2,  # Maps to "complete" status
                "Origins": [{"Id": 126, "Name": "Leadership Meeting"}],
            },
        ]

        # Create mock responses for each goal
        mock_create_responses = []
        for goal_data in created_goals:
            mock_response = MagicMock()
            mock_response.json.return_value = goal_data
            mock_response.raise_for_status = MagicMock()
            mock_create_responses.append(mock_response)

        # Set up side effects
        mock_async_client.post.side_effect = mock_create_responses

        # Test data
        goals_to_create = [
            {"title": "Q1 Revenue Target", "meeting_id": 125},
            {"title": "Product Launch", "meeting_id": 125, "user_id": 789},
            {"title": "Team Expansion", "meeting_id": 126},
        ]

        # Call the method
        result = await async_client.goal.create_many(goals_to_create)

        # Verify the result
        assert len(result.successful) == 3
        assert len(result.failed) == 0
        assert all(isinstance(goal, CreatedGoalInfo) for goal in result.successful)
        assert result.successful[0].id == 100
        assert result.successful[0].title == "Q1 Revenue Target"
        assert result.successful[0].status == "on"
        assert result.successful[1].id == 101
        assert result.successful[1].title == "Product Launch"
        assert result.successful[1].status == "off"
        assert result.successful[2].id == 102
        assert result.successful[2].status == "complete"

        # Verify API calls - should be 3 posts for goals
        assert mock_async_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_create_many_partial_failure(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where some goals fail."""
        # Mock responses - 1st succeeds, 2nd fails with 400, 3rd fails with 500
        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {
            "Id": 200,
            "Name": "Success Goal",
            "AccountableUserId": 1,
            "AccountableUserInitials": "JD",
            "AccountableUserName": "John Doe",
            "DueDate": "2024-03-31T00:00:00Z",
            "Owner": {"Id": 1, "Name": "John Doe"},
            "CreateTime": "2024-01-01T10:00:00Z",
            "Completion": 1,
            "Origins": [{"Id": 125, "Name": "Team Meeting"}],
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
        goals_to_create = [
            {"title": "Success Goal", "meeting_id": 125},
            {"title": "Bad Request Goal", "meeting_id": 125},
            {"title": "Server Error Goal", "meeting_id": 126},
        ]

        # Call the method
        result = await async_client.goal.create_many(goals_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.successful[0].id == 200
        assert result.successful[0].title == "Success Goal"

        # Check failed items
        assert result.failed[0].index == 1
        assert result.failed[0].input_data == goals_to_create[1]
        assert "Bad Request" in result.failed[0].error

        assert result.failed[1].index == 2
        assert result.failed[1].input_data == goals_to_create[2]
        assert "Internal Server Error" in result.failed[1].error

    @pytest.mark.asyncio
    async def test_create_many_empty_list(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with an empty list."""
        # Call the method with empty list
        result = await async_client.goal.create_many([])

        # Verify the result
        assert len(result.successful) == 0
        assert len(result.failed) == 0

        # Verify no API calls were made
        mock_async_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_many_validation_errors(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with validation errors (missing required fields)."""
        # Test data with missing required fields
        goals_to_create = [
            {"title": "Valid Goal", "meeting_id": 125},  # Valid
            {"title": "Missing Meeting ID"},  # Missing meeting_id
            {"meeting_id": 125},  # Missing title
            {},  # Missing both required fields
        ]

        # Mock successful create response for valid goal
        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {
            "Id": 300,
            "Name": "Valid Goal",
            "AccountableUserId": 1,
            "AccountableUserInitials": "JD",
            "AccountableUserName": "John Doe",
            "DueDate": "2024-03-31T00:00:00Z",
            "Owner": {"Id": 1, "Name": "John Doe"},
            "CreateTime": "2024-01-01T10:00:00Z",
            "Completion": 1,
            "Origins": [{"Id": 125, "Name": "Team Meeting"}],
        }
        mock_create_response.raise_for_status = MagicMock()

        # Set up mocks
        mock_async_client.post.return_value = mock_create_response

        # Call the method
        result = await async_client.goal.create_many(goals_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 3
        assert result.successful[0].id == 300

        # Check validation errors
        assert result.failed[0].index == 1
        assert "meeting_id is required" in result.failed[0].error

        assert result.failed[1].index == 2
        assert "title is required" in result.failed[1].error

        assert result.failed[2].index == 3
        assert "title is required" in result.failed[2].error

        # Only one successful creation should have been attempted
        assert mock_async_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_create_many_concurrent_execution(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test that create_many executes operations concurrently."""
        import time

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
                "Id": len(call_times) + 400,
                "Name": f"Goal {len(call_times)}",
                "AccountableUserId": 1,
                "AccountableUserInitials": "JD",
                "AccountableUserName": "John Doe",
                "DueDate": "2024-03-31T00:00:00Z",
                "Owner": {"Id": 1, "Name": "John Doe"},
                "CreateTime": "2024-01-01T10:00:00Z",
                "Completion": 1,
                "Origins": [{"Id": 125, "Name": "Team Meeting"}],
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        # Set up mocks
        mock_async_client.post.side_effect = delayed_post

        # Create multiple goals
        goals_to_create = [{"title": f"Goal {i}", "meeting_id": 125} for i in range(5)]

        # Call the method with max_concurrent=3
        start_time = time.time()
        result = await async_client.goal.create_many(goals_to_create, max_concurrent=3)
        total_time = time.time() - start_time

        # Verify all were successful
        assert len(result.successful) == 5
        assert len(result.failed) == 0

        # Verify concurrent execution
        # With max_concurrent=3 and 5 goals with 0.1s delay each:
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
