"""Tests for async todo operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import Todo


class TestAsyncTodoOperations:
    """Test cases for AsyncTodoOperations."""

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
    async def test_list_user_todos(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test listing todos for a user."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock todos response
        todos_data = [
            {
                "Id": 1,
                "Name": "Complete report",
                "DetailsUrl": "https://example.com/todo/1",
                "DueDate": "2024-01-08T10:00:00Z",
                "CompleteTime": None,
                "CreateTime": "2024-01-01T10:00:00Z",
                "OriginId": 123,
                "Origin": "Weekly Meeting",
                "Complete": False,
            },
            {
                "Id": 2,
                "Name": "Review code",
                "DetailsUrl": "https://example.com/todo/2",
                "DueDate": "2024-01-09T10:00:00Z",
                "CompleteTime": "2024-01-07T15:00:00Z",
                "CreateTime": "2024-01-02T10:00:00Z",
                "OriginId": 124,
                "Origin": "Sprint Planning",
                "Complete": True,
            },
        ]

        mock_todos_response = MagicMock()
        mock_todos_response.json.return_value = todos_data
        mock_todos_response.raise_for_status = MagicMock()

        # Set up side effect for different URLs
        def get_side_effect(url: str) -> MagicMock:
            if url == "users/mine":
                return mock_user_response
            elif url == "todo/user/456":
                return mock_todos_response
            else:
                raise ValueError(f"Unexpected URL: {url}")

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        result = await async_client.todo.list()

        # Verify the result
        assert len(result) == 2
        assert isinstance(result[0], Todo)
        assert result[0].id == 1
        assert result[0].name == "Complete report"
        assert result[0].complete is False
        assert result[1].id == 2
        assert result[1].name == "Review code"
        assert result[1].complete is True

        # Verify the API calls
        assert mock_async_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_list_meeting_todos(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test listing todos for a meeting."""
        # Mock todos response
        todos_data = [
            {
                "Id": 3,
                "Name": "Action item from meeting",
                "DetailsUrl": "https://example.com/todo/3",
                "DueDate": "2024-01-10T10:00:00Z",
                "CompleteTime": None,
                "CreateTime": "2024-01-03T10:00:00Z",
                "OriginId": 125,
                "Origin": "Project Review",
                "Complete": False,
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = todos_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.todo.list(meeting_id=125)

        # Verify the result
        assert len(result) == 1
        assert result[0].id == 3
        assert result[0].name == "Action item from meeting"

        # Verify the API call
        mock_async_client.get.assert_called_once_with("L10/125/todos")

    @pytest.mark.asyncio
    async def test_create_for_user(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test creating a todo for a user."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock create response
        created_todo = {
            "Id": 4,
            "Name": "New Task",
            "DetailsUrl": "https://example.com/todo/4",
            "DueDate": "2024-01-15T10:00:00Z",
            "CreateTime": "2024-01-05T10:00:00Z",
        }

        mock_create_response = MagicMock()
        mock_create_response.json.return_value = created_todo
        mock_create_response.raise_for_status = MagicMock()

        # Set up mock responses
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.return_value = mock_create_response

        # Call the method
        result = await async_client.todo.create(
            title="New Task",
            due_date="2024-01-15",
            notes="Important task",
        )

        # Verify the result
        assert isinstance(result, Todo)
        assert result.id == 4
        assert result.name == "New Task"

        # Verify the API calls
        mock_async_client.get.assert_called_once_with("users/mine")
        mock_async_client.post.assert_called_once()
        post_args = mock_async_client.post.call_args
        assert post_args[0][0] == "todo/create"
        payload = post_args[1]["json"]
        assert payload["title"] == "New Task"
        assert payload["dueDate"] == "2024-01-15"
        assert payload["notes"] == "Important task"
        assert payload["accountableUserId"] == 456

    @pytest.mark.asyncio
    async def test_create_for_meeting(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test creating a todo for a meeting."""
        # Mock create response
        created_todo = {
            "Id": 5,
            "Name": "Meeting Action Item",
            "DetailsUrl": "https://example.com/todo/5",
            "DueDate": "2024-01-20T10:00:00Z",
            "CreateTime": "2024-01-06T10:00:00Z",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = created_todo
        mock_response.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_response

        # Call the method
        result = await async_client.todo.create(
            title="Meeting Action Item",
            due_date="2024-01-20",
            meeting_id=125,
            user_id=789,
        )

        # Verify the result
        assert isinstance(result, Todo)
        assert result.id == 5
        assert result.name == "Meeting Action Item"

        # Verify the API call
        mock_async_client.post.assert_called_once()
        post_args = mock_async_client.post.call_args
        assert post_args[0][0] == "todo/createmeetingtodo"
        payload = post_args[1]["json"]
        assert payload["title"] == "Meeting Action Item"
        assert payload["meetingid"] == 125
        assert payload["accountableUserId"] == 789

    @pytest.mark.asyncio
    async def test_complete(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test completing a todo."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.is_success = True

        mock_async_client.post.return_value = mock_response

        # Call the method
        result = await async_client.todo.complete(todo_id=1)

        # Verify the result
        assert result is True

        # Verify the API call
        mock_async_client.post.assert_called_once_with(
            "todo/1/complete?status=true"
        )

    @pytest.mark.asyncio
    async def test_update(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test updating a todo."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_response

        mock_response.status_code = 200
        mock_async_client.put.return_value = mock_response

        # Call the method
        result = await async_client.todo.update(
            todo_id=1,
            title="Updated Task",
            due_date="2024-12-01",
        )

        # Verify the result
        assert isinstance(result, Todo)
        assert result.id == 1
        assert result.name == "Updated Task"

        # Verify the API call
        mock_async_client.put.assert_called_once()
        put_args = mock_async_client.put.call_args
        assert put_args[0][0] == "todo/1"
        payload = put_args[1]["json"]
        assert payload["title"] == "Updated Task"
        assert payload["dueDate"] == "2024-12-01"
