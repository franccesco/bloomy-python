"""Tests for async todo operations."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import Todo


class TestAsyncTodoOperations:
    """Test cases for AsyncTodoOperations."""

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
        mock_async_client.post.assert_called_once_with("todo/1/complete?status=true")

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

    @pytest.mark.asyncio
    async def test_create_many_all_successful(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where all todos are created successfully."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock create responses for each todo
        created_todos = [
            {
                "Id": 100,
                "Name": "Todo 1",
                "DetailsUrl": "https://example.com/todo/100",
                "DueDate": "2024-01-15T10:00:00Z",
                "CreateTime": "2024-01-05T10:00:00Z",
            },
            {
                "Id": 101,
                "Name": "Todo 2",
                "DetailsUrl": "https://example.com/todo/101",
                "DueDate": "2024-01-16T10:00:00Z",
                "CreateTime": "2024-01-05T10:00:00Z",
            },
            {
                "Id": 102,
                "Name": "Todo 3",
                "DetailsUrl": "https://example.com/todo/102",
                "DueDate": None,
                "CreateTime": "2024-01-05T10:00:00Z",
            },
        ]

        # Create mock responses for each todo
        mock_create_responses = []
        for todo_data in created_todos:
            mock_response = MagicMock()
            mock_response.json.return_value = todo_data
            mock_response.raise_for_status = MagicMock()
            mock_create_responses.append(mock_response)

        # Set up side effects
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.side_effect = mock_create_responses

        # Test data
        todos_to_create = [
            {"title": "Todo 1", "meeting_id": 125, "due_date": "2024-01-15"},
            {
                "title": "Todo 2",
                "meeting_id": 125,
                "due_date": "2024-01-16",
                "user_id": 789,
            },
            {"title": "Todo 3", "meeting_id": 126, "notes": "Important task"},
        ]

        # Call the method
        result = await async_client.todo.create_many(todos_to_create)

        # Verify the result
        assert len(result.successful) == 3
        assert len(result.failed) == 0
        assert all(isinstance(todo, Todo) for todo in result.successful)
        assert result.successful[0].id == 100
        assert result.successful[1].id == 101
        assert result.successful[2].id == 102

        # Verify API calls - should be 1 get for user ID + 3 posts for todos
        assert mock_async_client.get.call_count == 1
        assert mock_async_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_create_many_partial_failure(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where some todos fail."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock responses - 1st succeeds, 2nd fails with 400, 3rd fails with 500
        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {
            "Id": 200,
            "Name": "Success Todo",
            "DetailsUrl": "https://example.com/todo/200",
            "CreateTime": "2024-01-05T10:00:00Z",
        }
        mock_success_response.raise_for_status = MagicMock()

        # Create a 400 error response
        from httpx import HTTPStatusError, Response

        mock_400_response = Response(400, json={"error": "Bad Request"})
        mock_400_error = HTTPStatusError(
            "Bad Request", request=None, response=mock_400_response
        )

        # Create a 500 error response
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
        todos_to_create = [
            {"title": "Success Todo", "meeting_id": 125},
            {"title": "Bad Request Todo", "meeting_id": 125},
            {"title": "Server Error Todo", "meeting_id": 126},
        ]

        # Call the method
        result = await async_client.todo.create_many(todos_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.successful[0].id == 200
        assert result.successful[0].name == "Success Todo"

        # Check failed items
        assert result.failed[0].index == 1
        assert result.failed[0].input_data == todos_to_create[1]
        assert "Bad Request" in result.failed[0].error

        assert result.failed[1].index == 2
        assert result.failed[1].input_data == todos_to_create[2]
        assert "Internal Server Error" in result.failed[1].error

    @pytest.mark.asyncio
    async def test_create_many_empty_list(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with an empty list."""
        # Call the method with empty list
        result = await async_client.todo.create_many([])

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
        todos_to_create = [
            {"title": "Valid Todo", "meeting_id": 125},  # Valid
            {"meeting_id": 125},  # Missing title
            {"title": "Missing Meeting ID"},  # Missing meeting_id
            {},  # Missing both required fields
        ]

        # Mock user ID response for valid todo
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock successful create response for valid todo
        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {
            "Id": 300,
            "Name": "Valid Todo",
            "DetailsUrl": "https://example.com/todo/300",
            "CreateTime": "2024-01-05T10:00:00Z",
        }
        mock_create_response.raise_for_status = MagicMock()

        # Set up mocks
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.return_value = mock_create_response

        # Call the method
        result = await async_client.todo.create_many(todos_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 3
        assert result.successful[0].id == 300

        # Check validation errors
        assert result.failed[0].index == 1
        assert "title is required" in result.failed[0].error

        assert result.failed[1].index == 2
        assert "meeting_id is required" in result.failed[1].error

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
                "Id": len(call_times) + 400,
                "Name": f"Todo {len(call_times)}",
                "DetailsUrl": f"https://example.com/todo/{len(call_times) + 400}",
                "CreateTime": "2024-01-05T10:00:00Z",
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        # Set up mocks
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.side_effect = delayed_post

        # Create multiple todos
        todos_to_create = [{"title": f"Todo {i}", "meeting_id": 125} for i in range(5)]

        # Call the method with max_concurrent=3
        start_time = time.time()
        result = await async_client.todo.create_many(todos_to_create, max_concurrent=3)
        total_time = time.time() - start_time

        # Verify all were successful
        assert len(result.successful) == 5
        assert len(result.failed) == 0

        # Verify concurrent execution
        # With max_concurrent=3 and 5 todos with 0.1s delay each:
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
