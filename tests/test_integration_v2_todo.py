"""Integration tests for v2 (GraphQL) to-do operations against the real API.

Runs against the dedicated "SDK v2 API" test meeting only, and archives
everything it creates.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from bloomy import AsyncClient, Client
from bloomy.v2.models import Todo

MEETING_ID = 349524  # "v2 API" test meeting

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> Client:
    """Create a real Bloomy client for integration tests.

    Yields:
        A configured Client instance.

    """
    api_key = os.environ.get("BG_API_KEY")
    if not api_key:
        pytest.skip("BG_API_KEY not set")
    c = Client(api_key=api_key)
    yield c
    c.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    """Create a real async Bloomy client for integration tests.

    Yields:
        A configured AsyncClient instance.

    """
    api_key = os.environ.get("BG_API_KEY")
    if not api_key:
        pytest.skip("BG_API_KEY not set")
    c = AsyncClient(api_key=api_key)
    yield c
    await c.close()


def _title(tag: str) -> str:
    return f"SDK v2 integration test to-do {tag}"


def _poll_sync(
    fn: Callable[[], Todo],
    predicate: Callable[[Todo], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Todo:
    """Poll `fn()` until `predicate(result)` is true (notes pads lag a bit).

    Returns:
        The last polled `Todo`.

    """
    result = fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        time.sleep(delay)
        result = fn()
    return result


async def _poll_async(
    fn: Callable[[], Awaitable[Todo]],
    predicate: Callable[[Todo], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Todo:
    """Async equivalent of `_poll_sync`.

    Returns:
        The last polled `Todo`.

    """
    result = await fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        await asyncio.sleep(delay)
        result = await fn()
    return result


class TestTodoLifecycleSync:
    """Full CRUD lifecycle tests for sync v2 to-do operations."""

    def test_full_lifecycle(self, client: Client) -> None:
        """Create -> details -> list -> update -> complete -> reopen -> archive."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = client.v2.todo.create(
            title, meeting_id=MEETING_ID, notes="Lifecycle notes"
        )
        try:
            assert isinstance(created, Todo)
            assert created.title == title
            assert created.owner is not None
            assert created.meeting is not None and created.meeting.id == MEETING_ID
            assert created.completed is False
            assert created.archived is False
            assert created.due_date is not None

            details = _poll_sync(
                lambda: client.v2.todo.details(created.id),
                lambda t: t.notes is not None,
            )
            assert details.notes == "Lifecycle notes"

            listed = client.v2.todo.list(meeting_id=MEETING_ID)
            assert any(t.id == created.id for t in listed)

            updated = client.v2.todo.update(created.id, title=f"{title} (updated)")
            assert updated.title == f"{title} (updated)"

            completed = client.v2.todo.complete(created.id)
            assert completed.completed is True
            assert completed.completed_date is not None

            reopened = client.v2.todo.reopen(created.id)
            assert reopened.completed is False
            assert reopened.completed_date is None
        finally:
            # Cleanup: archive regardless of where the test got to.
            client.v2.todo.archive(created.id)

    def test_archive_and_restore(self, client: Client) -> None:
        """`archive()`/`restore()` toggle the `archived` flag."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.todo.create(_title(tag), meeting_id=MEETING_ID)

        try:
            archived = client.v2.todo.archive(created.id)
            assert archived.archived is True

            archived_list = client.v2.todo.list(
                meeting_id=MEETING_ID, include_archived=True
            )
            assert any(t.id == created.id for t in archived_list)

            restored = client.v2.todo.restore(created.id)
            assert restored.archived is False
        finally:
            client.v2.todo.archive(created.id)

    def test_personal_todo(self, client: Client) -> None:
        """`create()` without `meeting_id` makes a personal to-do."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.todo.create(_title(tag))

        try:
            assert created.meeting is None

            listed = client.v2.todo.list()
            assert any(t.id == created.id for t in listed)
        finally:
            client.v2.todo.archive(created.id)

    def test_list_include_flags_by_meeting(self, client: Client) -> None:
        """Each include-flag combination lists the to-dos it should, live.

        The default and `include_completed` lists read `todosActives` (which
        keeps completed to-dos and drops archived ones); `include_archived`
        lists read `todos`.
        """
        tag = uuid.uuid4().hex[:8]
        created = client.v2.todo.create(_title(tag), meeting_id=MEETING_ID)

        def listed(**flags: bool) -> bool:
            todos = client.v2.todo.list(meeting_id=MEETING_ID, **flags)
            return any(t.id == created.id for t in todos)

        try:
            assert listed()

            client.v2.todo.complete(created.id)
            assert not listed()
            assert listed(include_completed=True)

            client.v2.todo.archive(created.id)
            assert not listed(include_completed=True)
            assert not listed(include_archived=True)
            assert listed(include_completed=True, include_archived=True)
        finally:
            client.v2.todo.archive(created.id)

    def test_create_result_matches_details(self, client: Client) -> None:
        """`create()`'s result (no re-read) matches a later `details()` read.

        `created_date` is compared to the second: the mutation result keeps
        sub-second precision that the stored value rounds away.
        """
        tag = uuid.uuid4().hex[:8]
        created = client.v2.todo.create(_title(tag), meeting_id=MEETING_ID)

        try:
            details = client.v2.todo.details(created.id)
            assert created.model_dump(exclude={"created_date"}) == details.model_dump(
                exclude={"created_date"}
            )
            delta = created.created_date - details.created_date
            assert abs(delta.total_seconds()) < 1
        finally:
            client.v2.todo.archive(created.id)

    def test_list_requires_only_one_scope(self, client: Client) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        with pytest.raises(ValueError, match="Cannot specify both meeting_id and"):
            client.v2.todo.list(meeting_id=MEETING_ID, user_id=1305290)

    def test_update_requires_a_field(self, client: Client) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            client.v2.todo.update(1)


class TestTodoLifecycleAsync:
    """Full CRUD lifecycle tests for async v2 to-do operations."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Create -> details -> update -> complete -> reopen -> archive."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = await async_client.v2.todo.create(
            title, meeting_id=MEETING_ID, notes="Async lifecycle notes"
        )
        try:
            assert created.title == title

            details = await _poll_async(
                lambda: async_client.v2.todo.details(created.id),
                lambda t: t.notes is not None,
            )
            assert details.notes == "Async lifecycle notes"

            updated = await async_client.v2.todo.update(
                created.id, title=f"{title} (updated)"
            )
            assert updated.title == f"{title} (updated)"

            completed = await async_client.v2.todo.complete(created.id)
            assert completed.completed is True

            reopened = await async_client.v2.todo.reopen(created.id)
            assert reopened.completed is False
        finally:
            await async_client.v2.todo.archive(created.id)

    @pytest.mark.asyncio
    async def test_archive_and_restore(self, async_client: AsyncClient) -> None:
        """`archive()`/`restore()` toggle the `archived` flag."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.v2.todo.create(_title(tag), meeting_id=MEETING_ID)

        try:
            archived = await async_client.v2.todo.archive(created.id)
            assert archived.archived is True

            restored = await async_client.v2.todo.restore(created.id)
            assert restored.archived is False
        finally:
            await async_client.v2.todo.archive(created.id)

    @pytest.mark.asyncio
    async def test_update_requires_a_field(self, async_client: AsyncClient) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            await async_client.v2.todo.update(1)
