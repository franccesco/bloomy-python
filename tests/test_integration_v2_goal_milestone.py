"""Integration tests for v2 (GraphQL) goal and milestone operations against the API.

Runs against the dedicated "SDK v2 API" test meeting only, and archives
everything it creates (goals cannot be deleted through the GraphQL API,
only archived; milestones are deleted outright).
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
from bloomy.v2.models import Goal, GoalStatus

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
    return f"SDK v2 integration test goal {tag}"


def _poll_sync(
    fn: Callable[[], Goal],
    predicate: Callable[[Goal], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Goal:
    """Poll `fn()` until `predicate(result)` is true (notes pads lag a bit).

    Returns:
        The last polled `Goal`.

    """
    result = fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        time.sleep(delay)
        result = fn()
    return result


async def _poll_async(
    fn: Callable[[], Awaitable[Goal]],
    predicate: Callable[[Goal], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Goal:
    """Async equivalent of `_poll_sync`.

    Returns:
        The last polled `Goal`.

    """
    result = await fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        await asyncio.sleep(delay)
        result = await fn()
    return result


class TestGoalMilestoneLifecycleSync:
    """Full CRUD lifecycle tests for sync v2 goal and milestone operations."""

    def test_full_lifecycle(self, client: Client) -> None:
        """Create -> details -> list -> update -> archive -> restore.

        Exercises milestone create/update/complete/delete on the same goal.
        """
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = client.v2.goal.create(
            MEETING_ID,
            title,
            notes="Lifecycle notes",
            milestones=[{"title": "Initial milestone", "due_date": 1767225600}],
        )
        try:
            assert isinstance(created, Goal)
            assert created.title == title
            assert created.owner is not None
            assert created.status == GoalStatus.ON_TRACK
            assert created.archived is False
            assert any(m.title == "Initial milestone" for m in created.milestones)
            assert any(m.id == MEETING_ID for m in created.meetings)

            details = _poll_sync(
                lambda: client.v2.goal.details(created.id),
                lambda g: g.notes is not None,
            )
            assert details.notes == "Lifecycle notes"

            listed = client.v2.goal.list(meeting_id=MEETING_ID)
            assert any(g.id == created.id for g in listed)

            updated = client.v2.goal.update(
                created.id,
                title=f"{title} (updated)",
                status=GoalStatus.OFF_TRACK,
            )
            assert updated.title == f"{title} (updated)"
            assert updated.status == GoalStatus.OFF_TRACK

            # Milestones: list -> create -> update -> complete -> delete.
            initial_milestones = client.v2.milestone.list(created.id)
            assert len(initial_milestones) == 1
            seed_milestone = initial_milestones[0]

            new_milestone = client.v2.milestone.create(
                created.id, "Second milestone", 1767225600
            )
            assert new_milestone.goal_id == created.id
            assert new_milestone.completed is False

            renamed = client.v2.milestone.update(
                new_milestone.id, goal_id=created.id, title="Second milestone (renamed)"
            )
            assert renamed.title == "Second milestone (renamed)"

            completed_milestone = client.v2.milestone.complete(
                new_milestone.id, goal_id=created.id
            )
            assert completed_milestone.completed is True

            client.v2.milestone.delete(new_milestone.id)
            remaining = client.v2.milestone.list(created.id)
            assert all(m.id != new_milestone.id for m in remaining)
            assert any(m.id == seed_milestone.id for m in remaining)
        finally:
            # Cleanup: archive regardless of where the test got to (goals
            # cannot be deleted through the GraphQL API).
            client.v2.goal.archive(created.id)

    def test_archive_and_restore(self, client: Client) -> None:
        """`archive()`/`restore()` toggle the `archived` flag."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.goal.create(MEETING_ID, _title(tag))

        try:
            archived = client.v2.goal.archive(created.id)
            assert archived.archived is True

            restored = client.v2.goal.restore(created.id)
            assert restored.archived is False
            # Restoring re-attaches meeting links detached during archive.
            assert any(m.id == MEETING_ID for m in restored.meetings)
        finally:
            client.v2.goal.archive(created.id)

    def test_list_by_user_finds_the_same_goal(self, client: Client) -> None:
        """`list(user_id=...)` (via `user(id){ goals }`) also finds the goal.

        This is a different GraphQL path than `list(meeting_id=...)` (via
        `meeting(id){ goals }`), so it is worth checking on its own.
        """
        tag = uuid.uuid4().hex[:8]
        created = client.v2.goal.create(MEETING_ID, _title(tag))

        try:
            listed = client.v2.goal.list(user_id=client.v2.goal.user_id)
            assert any(g.id == created.id for g in listed)
        finally:
            client.v2.goal.archive(created.id)

    def test_list_requires_only_one_scope(self, client: Client) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        with pytest.raises(
            ValueError, match="Cannot specify both meeting_id and user_id"
        ):
            client.v2.goal.list(meeting_id=MEETING_ID, user_id=1305290)

    def test_update_requires_a_field(self, client: Client) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            client.v2.goal.update(1)

    def test_milestone_update_requires_a_field(self, client: Client) -> None:
        """Milestone `update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            client.v2.milestone.update(1, goal_id=1)


class TestGoalMilestoneLifecycleAsync:
    """Full CRUD lifecycle tests for async v2 goal and milestone operations."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Create -> details -> update -> milestone CRUD -> archive -> restore."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = await async_client.v2.goal.create(
            MEETING_ID, title, notes="Async lifecycle notes"
        )
        try:
            assert created.title == title

            details = await _poll_async(
                lambda: async_client.v2.goal.details(created.id),
                lambda g: g.notes is not None,
            )
            assert details.notes == "Async lifecycle notes"

            updated = await async_client.v2.goal.update(
                created.id, title=f"{title} (updated)"
            )
            assert updated.title == f"{title} (updated)"

            milestone = await async_client.v2.milestone.create(
                created.id, "Async milestone", 1767225600
            )
            assert milestone.goal_id == created.id

            completed_milestone = await async_client.v2.milestone.complete(
                milestone.id, goal_id=created.id
            )
            assert completed_milestone.completed is True

            await async_client.v2.milestone.delete(milestone.id)
            remaining = await async_client.v2.milestone.list(created.id)
            assert all(m.id != milestone.id for m in remaining)

            archived = await async_client.v2.goal.archive(created.id)
            assert archived.archived is True

            restored = await async_client.v2.goal.restore(created.id)
            assert restored.archived is False
        finally:
            await async_client.v2.goal.archive(created.id)

    @pytest.mark.asyncio
    async def test_update_requires_a_field(self, async_client: AsyncClient) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            await async_client.v2.goal.update(1)

    @pytest.mark.asyncio
    async def test_milestone_update_requires_a_field(
        self, async_client: AsyncClient
    ) -> None:
        """Milestone `update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            await async_client.v2.milestone.update(1, goal_id=1)
