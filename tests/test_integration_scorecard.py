"""Integration tests for scorecard operations against the real Bloom Growth API."""

from __future__ import annotations

import pytest

from bloomy import AsyncClient, Client
from bloomy.models import ScorecardItem, ScorecardWeek


@pytest.fixture(scope="module")
def client() -> Client:
    """Create a real Bloomy client using environment-provided API key.

    Yields:
        A Client instance.

    """
    c = Client()
    yield c
    c.close()


@pytest.fixture()
def async_client() -> AsyncClient:
    """Create a fresh async Bloomy client per test.

    Returns:
        An AsyncClient instance.

    """
    return AsyncClient()


@pytest.fixture(scope="module")
def measurable_id(client: Client) -> int:
    """Get the first measurable ID from the user's scorecard.

    Returns:
        The measurable ID.

    """
    items = client.scorecard.list(show_empty=True)
    assert len(items) > 0, "No scorecard items found for the test user"
    return items[0].measurable_id


@pytest.mark.integration
class TestScorecardCurrentWeek:
    """Tests for scorecard.current_week()."""

    def test_current_week_returns_scorecard_week(self, client: Client) -> None:
        """Current week returns a ScorecardWeek with valid fields."""
        week = client.scorecard.current_week()
        assert isinstance(week, ScorecardWeek)
        assert week.id > 0
        assert week.week_number > 0
        assert isinstance(week.week_start, str)
        assert isinstance(week.week_end, str)

    def test_current_week_field_semantics(self, client: Client) -> None:
        """Verify that week_start and week_end have correct semantic meaning.

        week_start comes from LocalDate.Date, week_end comes from ForWeek.
        ForWeek in weeks/current is a date string (the week end date).
        """
        week = client.scorecard.current_week()
        # Both should be date strings
        assert "T" in week.week_start, "week_start should be a datetime string"
        assert "T" in week.week_end, "week_end should be a datetime string"

    @pytest.mark.asyncio
    async def test_async_current_week(self, async_client: AsyncClient) -> None:
        """Async current_week returns the same structure."""
        async with async_client:
            week = await async_client.scorecard.current_week()
            assert isinstance(week, ScorecardWeek)
            assert week.week_number > 0


@pytest.mark.integration
class TestScorecardList:
    """Tests for scorecard.list()."""

    def test_list_returns_scorecard_items(self, client: Client) -> None:
        """List with show_empty returns all scorecard items."""
        items = client.scorecard.list(show_empty=True)
        assert isinstance(items, list)
        assert len(items) > 0
        for item in items:
            assert isinstance(item, ScorecardItem)
            assert item.measurable_id > 0
            assert isinstance(item.title, str)
            assert item.week_id > 0

    def test_list_filters_empty_by_default(self, client: Client) -> None:
        """List without show_empty filters out None values."""
        all_items = client.scorecard.list(show_empty=True)
        non_empty = client.scorecard.list(show_empty=False)
        assert len(non_empty) <= len(all_items)
        for item in non_empty:
            assert item.value is not None

    def test_list_with_week_offset_zero(self, client: Client) -> None:
        """List with week_offset=0 returns only current week items."""
        items = client.scorecard.list(show_empty=True, week_offset=0)
        assert isinstance(items, list)
        # All items should have the same week_id (the current week number)
        if items:
            week = client.scorecard.current_week()
            for item in items:
                assert item.week_id == week.week_number

    def test_list_with_negative_week_offset(self, client: Client) -> None:
        """List with negative week_offset returns previous week items."""
        items = client.scorecard.list(show_empty=True, week_offset=-1)
        assert isinstance(items, list)
        if items:
            week = client.scorecard.current_week()
            expected_week_id = week.week_number - 1
            for item in items:
                assert item.week_id == expected_week_id

    def test_list_by_meeting_id(self, client: Client) -> None:
        """List with meeting_id does not raise."""
        meetings = client.meeting.list()
        if meetings:
            items = client.scorecard.list(meeting_id=meetings[0].id, show_empty=True)
            assert isinstance(items, list)

    def test_list_raises_on_both_user_and_meeting(self, client: Client) -> None:
        """Providing both user_id and meeting_id raises ValueError."""
        with pytest.raises(ValueError, match="not both"):
            client.scorecard.list(user_id=1, meeting_id=1)

    @pytest.mark.asyncio
    async def test_async_list(self, async_client: AsyncClient) -> None:
        """Async list returns the same structure."""
        async with async_client:
            items = await async_client.scorecard.list(show_empty=True)
            assert isinstance(items, list)
            assert len(items) > 0


@pytest.mark.integration
class TestScorecardGet:
    """Tests for scorecard.get()."""

    def test_get_existing_measurable(self, client: Client, measurable_id: int) -> None:
        """Get an existing measurable returns a ScorecardItem."""
        item = client.scorecard.get(measurable_id=measurable_id)
        assert item is not None or isinstance(item, ScorecardItem)

    def test_get_nonexistent_measurable(self, client: Client) -> None:
        """Get a non-existent measurable returns None."""
        item = client.scorecard.get(measurable_id=999999999)
        assert item is None

    def test_get_with_week_offset(self, client: Client, measurable_id: int) -> None:
        """Get with week_offset returns correct week."""
        item = client.scorecard.get(measurable_id=measurable_id, week_offset=0)
        if item:
            week = client.scorecard.current_week()
            assert item.week_id == week.week_number

    @pytest.mark.asyncio
    async def test_async_get(
        self, async_client: AsyncClient, measurable_id: int
    ) -> None:
        """Async get returns the same result."""
        async with async_client:
            item = await async_client.scorecard.get(measurable_id=measurable_id)
            assert item is not None or isinstance(item, ScorecardItem)


@pytest.mark.integration
class TestScorecardScore:
    """Tests for scorecard.score()."""

    def test_score_update_and_verify(self, client: Client, measurable_id: int) -> None:
        """Score a measurable and verify the value is updated."""
        # Read the current value
        before = client.scorecard.get(measurable_id=measurable_id, week_offset=0)

        # Set a known value
        test_value = 42.0
        result = client.scorecard.score(
            measurable_id=measurable_id, score=test_value, week_offset=0
        )
        assert result is True

        # Verify the value
        after = client.scorecard.get(measurable_id=measurable_id, week_offset=0)
        assert after is not None
        assert after.value == test_value

        # Restore original value if it existed
        if before and before.value is not None:
            client.scorecard.score(
                measurable_id=measurable_id,
                score=before.value,
                week_offset=0,
            )

    @pytest.mark.asyncio
    async def test_async_score(
        self, async_client: AsyncClient, measurable_id: int
    ) -> None:
        """Async score updates correctly."""
        async with async_client:
            result = await async_client.scorecard.score(
                measurable_id=measurable_id, score=99.0, week_offset=0
            )
            assert result is True
