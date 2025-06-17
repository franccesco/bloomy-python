"""Tests for the async client."""

import pytest

from bloomy import AsyncClient


class TestAsyncClient:
    """Test cases for the AsyncClient."""

    @pytest.mark.asyncio
    async def test_init_with_api_key(self) -> None:
        """Test that AsyncClient initializes correctly with an API key."""
        client = AsyncClient(api_key="test-api-key")
        # Access headers through the httpx client for testing
        assert hasattr(client, "_client")
        headers = client._client.headers  # type: ignore[attr-defined]
        assert headers["Authorization"] == "Bearer test-api-key"
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test that AsyncClient works as a context manager."""
        async with AsyncClient(api_key="test-api-key") as client:
            # Access headers through the httpx client for testing
            assert hasattr(client, "_client")
            headers = client._client.headers  # type: ignore[attr-defined]
            assert headers["Authorization"] == "Bearer test-api-key"

    @pytest.mark.asyncio
    async def test_operations_initialization(self) -> None:
        """Test that all operations are correctly initialized."""
        async with AsyncClient(api_key="test-api-key") as client:
            assert hasattr(client, "user")
            assert hasattr(client, "meeting")
            assert hasattr(client, "todo")

            # Verify the correct async operation types
            from bloomy.operations.async_ import (
                AsyncMeetingOperations,
                AsyncTodoOperations,
                AsyncUserOperations,
            )

            assert isinstance(client.user, AsyncUserOperations)
            assert isinstance(client.meeting, AsyncMeetingOperations)
            assert isinstance(client.todo, AsyncTodoOperations)

    @pytest.mark.asyncio
    async def test_exit_with_exception(self) -> None:
        """Test __aexit__ with exception."""
        client = AsyncClient(api_key="test-api-key")
        await client.__aenter__()

        # Call __aexit__ with exception info
        result = await client.__aexit__(
            Exception,
            Exception("Test error"),
            None
        )

        # Should return None (not suppressing exception)
        assert result is None
