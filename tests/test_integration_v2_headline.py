"""Integration tests for v2 (GraphQL) headline operations against the real API.

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
from bloomy.v2.models import Headline

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
    return f"SDK v2 integration test headline {tag}"


def _poll_sync(
    fn: Callable[[], Headline],
    predicate: Callable[[Headline], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Headline:
    """Poll `fn()` until `predicate(result)` is true (notes pads lag a bit).

    Returns:
        The last polled `Headline`.

    """
    result = fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        time.sleep(delay)
        result = fn()
    return result


async def _poll_async(
    fn: Callable[[], Awaitable[Headline]],
    predicate: Callable[[Headline], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Headline:
    """Async equivalent of `_poll_sync`.

    Returns:
        The last polled `Headline`.

    """
    result = await fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        await asyncio.sleep(delay)
        result = await fn()
    return result


class TestHeadlineLifecycleSync:
    """Full CRUD lifecycle tests for sync v2 headline operations."""

    def test_full_lifecycle(self, client: Client) -> None:
        """Create -> details -> list -> update -> archive -> restore."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = client.v2.headline.create(MEETING_ID, title, notes="Lifecycle notes")
        try:
            assert isinstance(created, Headline)
            assert created.title == title
            assert created.owner is not None
            assert created.meeting is not None and created.meeting.id == MEETING_ID
            assert created.archived is False

            details = _poll_sync(
                lambda: client.v2.headline.details(created.id),
                lambda h: h.notes is not None,
            )
            assert details.notes == "Lifecycle notes"

            listed = client.v2.headline.list(meeting_id=MEETING_ID)
            assert any(h.id == created.id for h in listed)

            listed_by_user = client.v2.headline.list(user_id=created.owner.id)
            assert any(h.id == created.id for h in listed_by_user)

            updated = client.v2.headline.update(created.id, title=f"{title} (updated)")
            assert updated.title == f"{title} (updated)"

            archived = client.v2.headline.archive(created.id)
            assert archived.archived is True

            archived_list = client.v2.headline.list(
                meeting_id=MEETING_ID, include_archived=True
            )
            assert any(h.id == created.id for h in archived_list)

            open_by_user = client.v2.headline.list(user_id=created.owner.id)
            assert all(h.id != created.id for h in open_by_user)
            assert all(h.archived is False for h in open_by_user)
            all_by_user = client.v2.headline.list(
                user_id=created.owner.id, include_archived=True
            )
            assert any(h.id == created.id and h.archived for h in all_by_user)

            restored = client.v2.headline.restore(created.id)
            assert restored.archived is False
        finally:
            # Cleanup: archive regardless of where the test got to.
            client.v2.headline.archive(created.id)

    def test_list_requires_at_most_one_of_meeting_or_user(self, client: Client) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        with pytest.raises(
            ValueError, match="Cannot specify both meeting_id and user_id"
        ):
            client.v2.headline.list(meeting_id=MEETING_ID, user_id=1305290)

    def test_update_requires_a_field(self, client: Client) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            client.v2.headline.update(1)


class TestHeadlineLifecycleAsync:
    """Full CRUD lifecycle tests for async v2 headline operations."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Create -> details -> update -> archive -> restore."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = await async_client.v2.headline.create(
            MEETING_ID, title, notes="Async lifecycle notes"
        )
        try:
            assert created.title == title

            details = await _poll_async(
                lambda: async_client.v2.headline.details(created.id),
                lambda h: h.notes is not None,
            )
            assert details.notes == "Async lifecycle notes"

            updated = await async_client.v2.headline.update(
                created.id, title=f"{title} (updated)"
            )
            assert updated.title == f"{title} (updated)"

            archived = await async_client.v2.headline.archive(created.id)
            assert archived.archived is True

            restored = await async_client.v2.headline.restore(created.id)
            assert restored.archived is False
        finally:
            await async_client.v2.headline.archive(created.id)

    @pytest.mark.asyncio
    async def test_update_requires_a_field(self, async_client: AsyncClient) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            await async_client.v2.headline.update(1)
