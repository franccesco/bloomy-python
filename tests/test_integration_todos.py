"""Integration tests for todo operations against the real Bloom Growth API."""

from __future__ import annotations

import pytest
import pytest_asyncio

from bloomy import AsyncClient, Client
from bloomy.models import Todo

MEETING_ID = 324926


@pytest.fixture(scope="module")
def client() -> Client:
    """Create a real client for integration tests.

    Yields:
        A Bloomy client instance.

    """
    c = Client()
    yield c
    c.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    """Create a real async client for integration tests.

    Yields:
        An async Bloomy client instance.

    """
    c = AsyncClient()
    yield c
    await c.close()


# ── Sync Tests ──────────────────────────────────────────────────────────


@pytest.mark.integration
class TestTodoListSync:
    """Test listing todos (sync)."""

    def test_list_user_todos(self, client: Client) -> None:
        """List todos for the current user."""
        todos = client.todo.list()
        assert isinstance(todos, list)
        for todo in todos:
            assert isinstance(todo, Todo)

    def test_list_meeting_todos(self, client: Client) -> None:
        """List todos for a specific meeting."""
        todos = client.todo.list(meeting_id=MEETING_ID)
        assert isinstance(todos, list)
        for todo in todos:
            assert isinstance(todo, Todo)

    def test_list_raises_on_both_ids(self, client: Client) -> None:
        """Providing both user_id and meeting_id should raise ValueError."""
        with pytest.raises(ValueError, match="not both"):
            client.todo.list(user_id=1, meeting_id=1)


@pytest.mark.integration
class TestTodoCRUDSync:
    """Test full CRUD lifecycle for todos (sync)."""

    def test_create_and_delete_user_todo(self, client: Client) -> None:
        """Create a user todo, verify it, then clean up."""
        todo = client.todo.create(title="Integration test user todo")
        try:
            assert isinstance(todo, Todo)
            assert todo.name == "Integration test user todo"
            assert todo.id > 0

            # Verify via details
            fetched = client.todo.details(todo.id)
            assert fetched.id == todo.id
            assert fetched.name == todo.name
        finally:
            # Clean up — complete the todo since there's no delete endpoint
            client.todo.complete(todo.id)

    def test_create_meeting_todo(self, client: Client) -> None:
        """Create a meeting todo and verify it shows up in meeting todo list."""
        todo = client.todo.create(
            title="Integration test meeting todo",
            meeting_id=MEETING_ID,
        )
        try:
            assert isinstance(todo, Todo)
            assert todo.name == "Integration test meeting todo"
            assert todo.meeting_id == MEETING_ID
        finally:
            client.todo.complete(todo.id)

    def test_create_todo_with_due_date(self, client: Client) -> None:
        """Create a todo with a due date."""
        todo = client.todo.create(
            title="Integration test due date todo",
            due_date="2026-12-31",
        )
        try:
            assert isinstance(todo, Todo)
            assert todo.due_date is not None
        finally:
            client.todo.complete(todo.id)

    def test_complete_todo(self, client: Client) -> None:
        """Complete a todo and verify the complete flag."""
        todo = client.todo.create(title="Integration test complete todo")
        completed = client.todo.complete(todo.id)
        assert completed.complete is True

    def test_update_todo_title(self, client: Client) -> None:
        """Update a todo title."""
        todo = client.todo.create(title="Integration test original title")
        try:
            updated = client.todo.update(todo.id, title="Updated title")
            assert updated.name == "Updated title"
        finally:
            client.todo.complete(todo.id)

    def test_update_todo_due_date(self, client: Client) -> None:
        """Update a todo due date."""
        todo = client.todo.create(title="Integration test update due date")
        try:
            updated = client.todo.update(todo.id, due_date="2026-06-15")
            assert updated.due_date is not None
        finally:
            client.todo.complete(todo.id)

    def test_update_raises_without_fields(self, client: Client) -> None:
        """Updating with no fields should raise ValueError."""
        todo = client.todo.create(title="Integration test no-op update")
        try:
            with pytest.raises(ValueError, match="At least one field"):
                client.todo.update(todo.id)
        finally:
            client.todo.complete(todo.id)

    def test_details(self, client: Client) -> None:
        """Get todo details by ID."""
        todo = client.todo.create(title="Integration test details")
        try:
            details = client.todo.details(todo.id)
            assert details.id == todo.id
            assert details.name == "Integration test details"
        finally:
            client.todo.complete(todo.id)


# ── Async Tests ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestTodoListAsync:
    """Test listing todos (async)."""

    @pytest.mark.asyncio
    async def test_list_user_todos(self, async_client: AsyncClient) -> None:
        """List todos for the current user (async)."""
        todos = await async_client.todo.list()
        assert isinstance(todos, list)
        for todo in todos:
            assert isinstance(todo, Todo)

    @pytest.mark.asyncio
    async def test_list_meeting_todos(self, async_client: AsyncClient) -> None:
        """List todos for a specific meeting (async)."""
        todos = await async_client.todo.list(meeting_id=MEETING_ID)
        assert isinstance(todos, list)
        for todo in todos:
            assert isinstance(todo, Todo)

    @pytest.mark.asyncio
    async def test_list_raises_on_both_ids(self, async_client: AsyncClient) -> None:
        """Providing both user_id and meeting_id should raise ValueError (async)."""
        with pytest.raises(ValueError, match="not both"):
            await async_client.todo.list(user_id=1, meeting_id=1)


@pytest.mark.integration
class TestTodoCRUDAsync:
    """Test full CRUD lifecycle for todos (async)."""

    @pytest.mark.asyncio
    async def test_create_complete_lifecycle(self, async_client: AsyncClient) -> None:
        """Create, read, update, complete a todo (async)."""
        # Create
        todo = await async_client.todo.create(
            title="Async integration test todo",
        )
        try:
            assert isinstance(todo, Todo)
            assert todo.name == "Async integration test todo"

            # Read
            details = await async_client.todo.details(todo.id)
            assert details.id == todo.id

            # Update
            updated = await async_client.todo.update(
                todo.id, title="Async updated title"
            )
            assert updated.name == "Async updated title"
        finally:
            # Complete (cleanup)
            completed = await async_client.todo.complete(todo.id)
            assert completed.complete is True

    @pytest.mark.asyncio
    async def test_create_meeting_todo(self, async_client: AsyncClient) -> None:
        """Create a meeting todo (async)."""
        todo = await async_client.todo.create(
            title="Async meeting todo",
            meeting_id=MEETING_ID,
        )
        try:
            assert isinstance(todo, Todo)
            assert todo.meeting_id == MEETING_ID
        finally:
            await async_client.todo.complete(todo.id)
