"""Tests for async goal operations."""

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

        assert result is True
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

        assert result is True
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

        assert result is True
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

        assert result is True
        mock_async_client.put.assert_called_once_with("rocks/123/restore")
