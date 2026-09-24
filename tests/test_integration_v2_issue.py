"""Integration tests for v2 (GraphQL) issue operations against the real API.

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
from bloomy.v2.models import Issue

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
    return f"SDK v2 integration test issue {tag}"


def _poll_sync(
    fn: Callable[[], Issue],
    predicate: Callable[[Issue], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Issue:
    """Poll `fn()` until `predicate(result)` is true (notes pads lag a bit).

    Returns:
        The last polled `Issue`.

    """
    result = fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        time.sleep(delay)
        result = fn()
    return result


async def _poll_async(
    fn: Callable[[], Awaitable[Issue]],
    predicate: Callable[[Issue], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Issue:
    """Async equivalent of `_poll_sync`.

    Returns:
        The last polled `Issue`.

    """
    result = await fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        await asyncio.sleep(delay)
        result = await fn()
    return result


class TestIssueLifecycleSync:
    """Full CRUD lifecycle tests for sync v2 issue operations."""

    def test_full_lifecycle(self, client: Client) -> None:
        """Create -> details -> update -> solve -> reopen -> archive -> restore."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = client.v2.issue.create(MEETING_ID, title, notes="Lifecycle notes")
        try:
            assert isinstance(created, Issue)
            assert created.title == title
            assert created.owner is not None
            assert created.meeting is not None and created.meeting.id == MEETING_ID
            assert created.long_term is False
            assert created.completed is False
            assert created.archived is False

            details = _poll_sync(
                lambda: client.v2.issue.details(created.id),
                lambda i: i.notes is not None,
            )
            assert details.notes == "Lifecycle notes"

            listed = client.v2.issue.list(MEETING_ID)
            assert any(i.id == created.id for i in listed)

            updated = client.v2.issue.update(created.id, title=f"{title} (updated)")
            assert updated.title == f"{title} (updated)"

            solved = client.v2.issue.solve(created.id)
            assert solved.completed is True
            assert solved.completed_date is not None

            reopened = client.v2.issue.reopen(created.id)
            assert reopened.completed is False
            assert reopened.completed_date is None
        finally:
            # Cleanup: archive regardless of where the test got to.
            client.v2.issue.archive(created.id)

    def test_archive_and_restore(self, client: Client) -> None:
        """`archive()`/`restore()` toggle the `archived` flag."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.issue.create(MEETING_ID, _title(tag))

        try:
            archived = client.v2.issue.archive(created.id)
            assert archived.archived is True

            archived_list = client.v2.issue.list(MEETING_ID, include_archived=True)
            assert any(i.id == created.id for i in archived_list)

            restored = client.v2.issue.restore(created.id)
            assert restored.archived is False
        finally:
            client.v2.issue.archive(created.id)

    def test_long_term_toggle(self, client: Client) -> None:
        """`update(long_term=True)` moves an issue to `list(long_term=True)`."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.issue.create(MEETING_ID, _title(tag))

        try:
            long_term = client.v2.issue.update(created.id, long_term=True)
            assert long_term.long_term is True
            assert long_term.archived is False

            long_term_list = client.v2.issue.list(MEETING_ID, long_term=True)
            assert any(i.id == created.id for i in long_term_list)
        finally:
            client.v2.issue.update(created.id, long_term=False)
            client.v2.issue.archive(created.id)

    def test_archive_long_term_issue(self, client: Client) -> None:
        """Archiving a long-term issue removes it from the long-term list."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.issue.create(MEETING_ID, _title(tag), long_term=True)

        try:
            archived = client.v2.issue.archive(created.id)
            assert archived.archived is True
            assert archived.long_term is False

            long_term_list = client.v2.issue.list(MEETING_ID, long_term=True)
            assert all(i.id != created.id for i in long_term_list)
        finally:
            client.v2.issue.archive(created.id)

    def test_update_requires_a_field(self, client: Client) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            client.v2.issue.update(1)


class TestIssueLifecycleAsync:
    """Full CRUD lifecycle tests for async v2 issue operations."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Create -> details -> update -> solve -> reopen -> archive."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = await async_client.v2.issue.create(
            MEETING_ID, title, notes="Async lifecycle notes"
        )
        try:
            assert created.title == title

            details = await _poll_async(
                lambda: async_client.v2.issue.details(created.id),
                lambda i: i.notes is not None,
            )
            assert details.notes == "Async lifecycle notes"

            updated = await async_client.v2.issue.update(
                created.id, title=f"{title} (updated)"
            )
            assert updated.title == f"{title} (updated)"

            solved = await async_client.v2.issue.solve(created.id)
            assert solved.completed is True

            reopened = await async_client.v2.issue.reopen(created.id)
            assert reopened.completed is False
        finally:
            await async_client.v2.issue.archive(created.id)

    @pytest.mark.asyncio
    async def test_archive_and_restore(self, async_client: AsyncClient) -> None:
        """`archive()`/`restore()` toggle the `archived` flag."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.v2.issue.create(MEETING_ID, _title(tag))

        try:
            archived = await async_client.v2.issue.archive(created.id)
            assert archived.archived is True

            restored = await async_client.v2.issue.restore(created.id)
            assert restored.archived is False
        finally:
            await async_client.v2.issue.archive(created.id)

    @pytest.mark.asyncio
    async def test_update_requires_a_field(self, async_client: AsyncClient) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            await async_client.v2.issue.update(1)
