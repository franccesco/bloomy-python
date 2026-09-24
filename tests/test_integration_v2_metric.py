"""Integration tests for v2 (GraphQL) metric operations against the real API.

Runs against the dedicated "SDK v2 API" test meeting only, and archives
everything it creates (metrics cannot be un-archived through the GraphQL
API, only archived -- there is no `restore()`).
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from bloomy import AsyncClient, Client
from bloomy.exceptions import GraphQLError
from bloomy.v2.models import Metric, MetricFrequency, MetricRule, MetricUnit

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
    return f"SDK v2 integration test metric {tag}"


def _poll_sync(
    fn: Callable[[], Metric],
    predicate: Callable[[Metric], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Metric:
    """Poll `fn()` until `predicate(result)` is true (notes pads lag a bit).

    Returns:
        The last polled `Metric`.

    """
    result = fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        time.sleep(delay)
        result = fn()
    return result


async def _poll_async(
    fn: Callable[[], Awaitable[Metric]],
    predicate: Callable[[Metric], bool],
    attempts: int = 6,
    delay: float = 1.5,
) -> Metric:
    """Async equivalent of `_poll_sync`.

    Returns:
        The last polled `Metric`.

    """
    result = await fn()
    for _ in range(attempts):
        if predicate(result):
            return result
        await asyncio.sleep(delay)
        result = await fn()
    return result


class TestMetricLifecycleSync:
    """Full CRUD + scoring lifecycle tests for sync v2 metric operations."""

    def test_full_lifecycle(self, client: Client) -> None:
        """Create -> details -> list -> update -> score -> archive."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = client.v2.metric.create(
            MEETING_ID,
            title,
            goal=100,
            notes="Lifecycle notes",
        )
        try:
            assert isinstance(created, Metric)
            assert created.title == title
            assert created.owner is not None
            assert created.units == MetricUnit.NONE
            assert created.rule == MetricRule.GREATER_THAN
            assert created.frequency == MetricFrequency.WEEKLY
            assert created.goal == 100.0
            assert created.archived is False
            assert created.is_externally_synced is False

            details = _poll_sync(
                lambda: client.v2.metric.details(created.id),
                lambda m: m.notes is not None,
            )
            assert details.notes == "Lifecycle notes"

            listed = client.v2.metric.list(meeting_id=MEETING_ID)
            assert any(m.id == created.id for m in listed)

            listed_by_frequency = client.v2.metric.list(
                meeting_id=MEETING_ID, frequency=MetricFrequency.WEEKLY
            )
            assert any(m.id == created.id for m in listed_by_frequency)

            listed_by_user = client.v2.metric.list(user_id=client.v2.metric.user_id)
            assert any(m.id == created.id for m in listed_by_user)

            updated = client.v2.metric.update(created.id, title=f"{title} (updated)")
            assert updated.title == f"{title} (updated)"

            # Scoring: set (upsert) -> re-set (same week) -> update -> clear.
            now = datetime.now(tz=UTC)
            score = client.v2.metric.set_score(created.id, 120, now)
            assert score.value == 120.0
            assert score.metric_id == created.id

            upserted = client.v2.metric.set_score(created.id, 130, now)
            assert upserted.id == score.id
            assert upserted.value == 130.0

            scores = client.v2.metric.scores(created.id)
            assert any(s.id == score.id and s.value == 130.0 for s in scores)

            edited = client.v2.metric.update_score(
                created.id, score.id, value=140, notes="edited"
            )
            assert edited.value == 140.0
            assert edited.notes == "edited"

            cleared = client.v2.metric.clear_score(created.id, score.id)
            assert cleared.value is None

            scores_without_empty = client.v2.metric.scores(created.id)
            assert all(s.id != score.id for s in scores_without_empty)

            scores_with_empty = client.v2.metric.scores(created.id, include_empty=True)
            assert any(s.id == score.id for s in scores_with_empty)
        finally:
            # Cleanup: archive regardless of where the test got to (there is
            # no restore -- see the module docstring).
            client.v2.metric.archive(created.id)

    def test_daily_set_score_falls_back_to_edit(self, client: Client) -> None:
        """A second `set_score()` on the same DAILY day edits, not duplicates."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.metric.create(
            MEETING_ID, _title(tag), frequency=MetricFrequency.DAILY
        )

        try:
            today = datetime.now(tz=UTC)
            first = client.v2.metric.set_score(created.id, 1, today)
            second = client.v2.metric.set_score(created.id, 2, today)

            assert second.id == first.id
            assert second.value == 2.0
        finally:
            client.v2.metric.archive(created.id)

    def test_set_score_unparseable_value_raises(self, client: Client) -> None:
        """`set_score()` raises when the value cannot be parsed as a number."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.metric.create(MEETING_ID, _title(tag))

        try:
            with pytest.raises(GraphQLError, match="could not be parsed"):
                client.v2.metric.set_score(
                    created.id, "not-a-number", datetime.now(tz=UTC)
                )
        finally:
            client.v2.metric.archive(created.id)

    def test_between_rule_uses_min_max_goal(self, client: Client) -> None:
        """`create(rule=BETWEEN, min_goal=..., max_goal=...)` round-trips."""
        tag = uuid.uuid4().hex[:8]
        created = client.v2.metric.create(
            MEETING_ID,
            _title(tag),
            rule=MetricRule.BETWEEN,
            min_goal=10,
            max_goal=20,
        )

        try:
            assert created.rule == MetricRule.BETWEEN
            assert created.min_goal == 10.0
        finally:
            client.v2.metric.archive(created.id)

    def test_create_goal_with_between_raises(self, client: Client) -> None:
        """`create(rule=BETWEEN, goal=...)` raises `ValueError` before any request."""
        with pytest.raises(ValueError, match="BETWEEN"):
            client.v2.metric.create(
                MEETING_ID, "unused", rule=MetricRule.BETWEEN, goal=10
            )

    def test_list_requires_only_one_scope(self, client: Client) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        with pytest.raises(
            ValueError, match="Cannot specify both meeting_id and user_id"
        ):
            client.v2.metric.list(meeting_id=MEETING_ID, user_id=1305290)

    def test_update_requires_a_field(self, client: Client) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            client.v2.metric.update(1)

    def test_update_score_requires_a_field(self, client: Client) -> None:
        """`update_score()` with neither `value` nor `notes` raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one of"):
            client.v2.metric.update_score(1, 1)


class TestMetricLifecycleAsync:
    """Full CRUD + scoring lifecycle tests for async v2 metric operations."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Create -> details -> update -> score -> archive."""
        tag = uuid.uuid4().hex[:8]
        title = _title(tag)

        created = await async_client.v2.metric.create(
            MEETING_ID, title, goal=50, notes="Async lifecycle notes"
        )
        try:
            assert created.title == title
            assert created.goal == 50.0

            details = await _poll_async(
                lambda: async_client.v2.metric.details(created.id),
                lambda m: m.notes is not None,
            )
            assert details.notes == "Async lifecycle notes"

            listed = await async_client.v2.metric.list(meeting_id=MEETING_ID)
            assert any(m.id == created.id for m in listed)

            updated = await async_client.v2.metric.update(
                created.id, title=f"{title} (updated)"
            )
            assert updated.title == f"{title} (updated)"

            now = datetime.now(tz=UTC)
            score = await async_client.v2.metric.set_score(created.id, 77, now)
            assert score.value == 77.0

            edited = await async_client.v2.metric.update_score(
                created.id, score.id, value=88
            )
            assert edited.value == 88.0

            cleared = await async_client.v2.metric.clear_score(created.id, score.id)
            assert cleared.value is None
        finally:
            await async_client.v2.metric.archive(created.id)

    @pytest.mark.asyncio
    async def test_daily_set_score_falls_back_to_edit(
        self, async_client: AsyncClient
    ) -> None:
        """A second `set_score()` on the same DAILY day edits, not duplicates."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.v2.metric.create(
            MEETING_ID, _title(tag), frequency=MetricFrequency.DAILY
        )

        try:
            today = datetime.now(tz=UTC)
            first = await async_client.v2.metric.set_score(created.id, 1, today)
            second = await async_client.v2.metric.set_score(created.id, 2, today)

            assert second.id == first.id
            assert second.value == 2.0
        finally:
            await async_client.v2.metric.archive(created.id)

    @pytest.mark.asyncio
    async def test_scores_time_range(self, async_client: AsyncClient) -> None:
        """`scores(start=..., end=...)` narrows the returned scores."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.v2.metric.create(MEETING_ID, _title(tag))

        try:
            now = datetime.now(tz=UTC)
            await async_client.v2.metric.set_score(created.id, 5, now)

            # Weekly scores are stored at the Sunday-anchored start of their
            # week (verified live), which can be up to 6 days before `now`;
            # widen the window well past that instead of assuming the score
            # timestamp is close to `now`.
            scores = await async_client.v2.metric.scores(
                created.id,
                start=now - timedelta(days=10),
                end=now + timedelta(days=3),
            )
            assert any(s.value == 5.0 for s in scores)
        finally:
            await async_client.v2.metric.archive(created.id)

    @pytest.mark.asyncio
    async def test_update_requires_a_field(self, async_client: AsyncClient) -> None:
        """`update()` with no fields raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one field"):
            await async_client.v2.metric.update(1)

    @pytest.mark.asyncio
    async def test_update_score_requires_a_field(
        self, async_client: AsyncClient
    ) -> None:
        """`update_score()` with neither `value` nor `notes` raises `ValueError`."""
        with pytest.raises(ValueError, match="At least one of"):
            await async_client.v2.metric.update_score(1, 1)
