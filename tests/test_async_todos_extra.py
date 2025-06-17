"""Additional tests for async todo operations to improve coverage."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import Todo


class TestAsyncTodoOperationsExtra:
    """Additional test cases for AsyncTodoOperations."""

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
    async def test_details(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test getting todo details."""
        # Mock the response data
        todo_data = {
            "Id": 789,
            "Name": "Test Todo",
            "DetailsUrl": "https://example.com/todo/789",
            "DueDate": "2024-12-31T10:00:00Z",
            "CreateTime": "2024-01-01T10:00:00Z",
            "CompleteTime": None,
            "Complete": False,
            "OriginId": 123,
            "Origin": "Team Meeting",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = todo_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.todo.details(789)

        # Verify the result
        assert isinstance(result, Todo)
        assert result.id == 789
        assert result.name == "Test Todo"
        assert result.meeting_id == 123
        assert result.meeting_name == "Team Meeting"

        # Verify the API call
        mock_async_client.get.assert_called_once_with("todo/789")

    @pytest.mark.asyncio
    async def test_update_raises_on_failure(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test that update raises error on failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status = MagicMock()

        mock_async_client.put.return_value = mock_response

        # Call the method and expect error
        with pytest.raises(RuntimeError, match="Failed to update todo"):
            await async_client.todo.update(
                todo_id=1,
                title="Updated Task",
            )

    @pytest.mark.asyncio
    async def test_update_no_fields_error(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test that update raises error when no fields provided."""
        # Call the method and expect error
        with pytest.raises(ValueError, match="At least one field must be provided"):
            await async_client.todo.update(todo_id=1)
