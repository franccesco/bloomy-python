"""Integration tests for goal operations against the real Bloom Growth API."""

from __future__ import annotations

import pytest
import pytest_asyncio

from bloomy import AsyncClient, Client
from bloomy.models import (
    ArchivedGoalInfo,
    CreatedGoalInfo,
    GoalInfo,
    GoalListResponse,
    GoalStatus,
)

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
class TestGoalListSync:
    """Test listing goals (sync)."""

    def test_list_active_goals(self, client: Client) -> None:
        """List active goals for the current user."""
        goals = client.goal.list()
        assert isinstance(goals, list)
        for goal in goals:
            assert isinstance(goal, GoalInfo)

    def test_list_with_archived(self, client: Client) -> None:
        """List goals including archived ones returns GoalListResponse."""
        result = client.goal.list(archived=True)
        assert isinstance(result, GoalListResponse)
        assert isinstance(result.active, list)
        assert isinstance(result.archived, list)
        for g in result.active:
            assert isinstance(g, GoalInfo)
        for g in result.archived:
            assert isinstance(g, ArchivedGoalInfo)


@pytest.mark.integration
class TestGoalCRUDSync:
    """Test full CRUD lifecycle for goals (sync)."""

    def test_create_and_delete_goal(self, client: Client) -> None:
        """Create a goal, verify it, then delete."""
        goal = client.goal.create(title="Integration test goal", meeting_id=MEETING_ID)
        try:
            assert isinstance(goal, CreatedGoalInfo)
            assert goal.title == "Integration test goal"
            assert goal.meeting_id == MEETING_ID
            assert goal.id > 0
        finally:
            client.goal.delete(goal.id)

    def test_update_goal_title(self, client: Client) -> None:
        """Update a goal title."""
        goal = client.goal.create(title="Goal original title", meeting_id=MEETING_ID)
        try:
            client.goal.update(goal.id, title="Goal updated title")

            # Verify via list
            goals = client.goal.list()
            assert isinstance(goals, list)
            updated = next((g for g in goals if g.id == goal.id), None)
            assert updated is not None
            assert updated.title == "Goal updated title"
        finally:
            client.goal.delete(goal.id)

    def test_update_goal_status_enum(self, client: Client) -> None:
        """Update a goal status using GoalStatus enum."""
        goal = client.goal.create(title="Goal status enum test", meeting_id=MEETING_ID)
        try:
            # Set to on-track
            client.goal.update(goal.id, status=GoalStatus.ON_TRACK)
            # Set to at-risk
            client.goal.update(goal.id, status=GoalStatus.AT_RISK)
            # Set to complete
            client.goal.update(goal.id, status=GoalStatus.COMPLETE)
        finally:
            client.goal.delete(goal.id)

    def test_update_goal_status_string(self, client: Client) -> None:
        """Update a goal status using string values."""
        goal = client.goal.create(
            title="Goal status string test", meeting_id=MEETING_ID
        )
        try:
            client.goal.update(goal.id, status="on")
            client.goal.update(goal.id, status="off")
            client.goal.update(goal.id, status="complete")
        finally:
            client.goal.delete(goal.id)

    def test_update_goal_invalid_status(self, client: Client) -> None:
        """Invalid status string should raise ValueError."""
        goal = client.goal.create(
            title="Goal invalid status test", meeting_id=MEETING_ID
        )
        try:
            with pytest.raises(ValueError, match="Invalid status value"):
                client.goal.update(goal.id, status="invalid")
        finally:
            client.goal.delete(goal.id)

    def test_archive_and_restore_goal(self, client: Client) -> None:
        """Archive a goal, verify it's archived, then restore it."""
        goal = client.goal.create(title="Goal archive test", meeting_id=MEETING_ID)
        try:
            # Archive
            client.goal.archive(goal.id)

            # Verify it appears in archived list
            result = client.goal.list(archived=True)
            assert isinstance(result, GoalListResponse)
            archived_ids = [g.id for g in result.archived]
            assert goal.id in archived_ids

            # Restore
            client.goal.restore(goal.id)

            # Verify it's back in active list
            goals = client.goal.list()
            assert isinstance(goals, list)
            active_ids = [g.id for g in goals]
            assert goal.id in active_ids
        finally:
            client.goal.delete(goal.id)

    def test_delete_goal(self, client: Client) -> None:
        """Delete a goal and verify it's gone."""
        goal = client.goal.create(title="Goal delete test", meeting_id=MEETING_ID)
        client.goal.delete(goal.id)

        # Verify gone from active list
        goals = client.goal.list()
        assert isinstance(goals, list)
        assert all(g.id != goal.id for g in goals)


@pytest.mark.integration
class TestGoalUpdateOwnerBug:
    """Test for the known bug: goal.update() always overwrites accountable_user.

    When calling goal.update(goal_id, title="new title") without passing
    accountable_user, the current implementation defaults accountable_user
    to self.user_id. This means the owner is silently overwritten even if
    the caller only intended to update the title.
    """

    def test_update_title_should_not_change_owner(self, client: Client) -> None:
        """Updating only the title should preserve the original owner.

        This test exposes the bug in goals.py line 158-159 where
        `accountable_user` defaults to `self.user_id` when None.
        """
        # Create a goal (owned by current user)
        goal = client.goal.create(
            title="Owner preservation test", meeting_id=MEETING_ID
        )
        try:
            # Get the original owner
            goals = client.goal.list()
            assert isinstance(goals, list)
            original = next(g for g in goals if g.id == goal.id)
            original_user_id = original.user_id

            # Update only the title — should NOT change owner
            client.goal.update(goal.id, title="Owner preservation updated")

            # Verify the owner is still the same
            goals = client.goal.list()
            assert isinstance(goals, list)
            updated = next(g for g in goals if g.id == goal.id)
            assert updated.title == "Owner preservation updated"
            assert updated.user_id == original_user_id, (
                f"Bug: owner changed from {original_user_id} to {updated.user_id} "
                f"when only updating title. goal.update() should not default "
                f"accountable_user to self.user_id when it's not provided."
            )
        finally:
            client.goal.delete(goal.id)


# ── Async Tests ─────────────────────────────────────────────────────────


@pytest.mark.integration
class TestGoalListAsync:
    """Test listing goals (async)."""

    @pytest.mark.asyncio
    async def test_list_active_goals(self, async_client: AsyncClient) -> None:
        """List active goals (async)."""
        goals = await async_client.goal.list()
        assert isinstance(goals, list)
        for goal in goals:
            assert isinstance(goal, GoalInfo)

    @pytest.mark.asyncio
    async def test_list_with_archived(self, async_client: AsyncClient) -> None:
        """List goals including archived (async)."""
        result = await async_client.goal.list(archived=True)
        assert isinstance(result, GoalListResponse)


@pytest.mark.integration
class TestGoalCRUDAsync:
    """Test full CRUD lifecycle for goals (async)."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Create, update, archive, restore, delete a goal (async)."""
        # Create
        goal = await async_client.goal.create(
            title="Async integration test goal", meeting_id=MEETING_ID
        )
        try:
            assert isinstance(goal, CreatedGoalInfo)
            assert goal.title == "Async integration test goal"

            # Update title
            await async_client.goal.update(goal.id, title="Async updated goal")

            # Update status
            await async_client.goal.update(goal.id, status=GoalStatus.ON_TRACK)

            # Archive
            await async_client.goal.archive(goal.id)

            # Restore
            await async_client.goal.restore(goal.id)
        finally:
            # Delete
            await async_client.goal.delete(goal.id)

    @pytest.mark.asyncio
    async def test_update_title_should_not_change_owner(
        self, async_client: AsyncClient
    ) -> None:
        """Async version: updating title should not change owner."""
        goal = await async_client.goal.create(
            title="Async owner preservation test", meeting_id=MEETING_ID
        )
        try:
            goals = await async_client.goal.list()
            assert isinstance(goals, list)
            original = next(g for g in goals if g.id == goal.id)
            original_user_id = original.user_id

            await async_client.goal.update(goal.id, title="Async owner updated")

            goals = await async_client.goal.list()
            assert isinstance(goals, list)
            updated = next(g for g in goals if g.id == goal.id)
            assert updated.user_id == original_user_id, (
                f"Bug: owner changed from {original_user_id} to {updated.user_id}"
            )
        finally:
            await async_client.goal.delete(goal.id)
