"""Integration tests for meeting operations against the real Bloom Growth API."""

from __future__ import annotations

import contextlib

import pytest

from bloomy import AsyncClient, Client
from bloomy.models import (
    MeetingAttendee,
    MeetingDetails,
    MeetingListItem,
    Todo,
)


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
def meeting_id(client: Client) -> int:
    """Get the first meeting ID from the user's meeting list.

    Returns:
        The meeting ID.

    """
    meetings = client.meeting.list()
    assert len(meetings) > 0, "No meetings found for the test user"
    return meetings[0].id


@pytest.fixture()
def temp_meeting(client: Client) -> int:
    """Create a temporary meeting and delete it after the test.

    Yields:
        The meeting ID.

    """
    result = client.meeting.create("Integration Test Meeting", add_self=True)
    mid = result["meeting_id"]
    yield mid
    with contextlib.suppress(Exception):
        client.meeting.delete(mid)


@pytest.mark.integration
class TestMeetingList:
    """Tests for meeting.list()."""

    def test_list_returns_meeting_list_items(self, client: Client) -> None:
        """Listing meetings returns a non-empty list of MeetingListItem."""
        meetings = client.meeting.list()
        assert isinstance(meetings, list)
        assert len(meetings) > 0
        for m in meetings:
            assert isinstance(m, MeetingListItem)
            assert m.id > 0
            assert isinstance(m.name, str)

    def test_list_with_explicit_user_id(self, client: Client) -> None:
        """Listing meetings with explicit user_id works."""
        user_id = client.user.details().id
        meetings = client.meeting.list(user_id=user_id)
        assert isinstance(meetings, list)

    @pytest.mark.asyncio
    async def test_async_list(self, async_client: AsyncClient) -> None:
        """Async list returns the same structure."""
        async with async_client:
            meetings = await async_client.meeting.list()
            assert isinstance(meetings, list)
            assert len(meetings) > 0
            for m in meetings:
                assert isinstance(m, MeetingListItem)


@pytest.mark.integration
class TestMeetingAttendees:
    """Tests for meeting.attendees()."""

    def test_attendees_returns_list(self, client: Client, meeting_id: int) -> None:
        """Attendees returns a list of MeetingAttendee."""
        attendees = client.meeting.attendees(meeting_id)
        assert isinstance(attendees, list)
        assert len(attendees) > 0
        for a in attendees:
            assert isinstance(a, MeetingAttendee)
            assert a.user_id > 0
            assert isinstance(a.name, str)

    @pytest.mark.asyncio
    async def test_async_attendees(
        self, async_client: AsyncClient, meeting_id: int
    ) -> None:
        """Async attendees returns the same structure."""
        async with async_client:
            attendees = await async_client.meeting.attendees(meeting_id)
            assert isinstance(attendees, list)
            assert len(attendees) > 0


@pytest.mark.integration
class TestMeetingIssues:
    """Tests for meeting.issues()."""

    def test_issues_returns_list(self, client: Client, meeting_id: int) -> None:
        """Issues returns a list (possibly empty)."""
        issues = client.meeting.issues(meeting_id)
        assert isinstance(issues, list)

    def test_issues_include_closed(self, client: Client, meeting_id: int) -> None:
        """Issues with include_closed does not raise."""
        issues = client.meeting.issues(meeting_id, include_closed=True)
        assert isinstance(issues, list)


@pytest.mark.integration
class TestMeetingTodos:
    """Tests for meeting.todos()."""

    def test_todos_returns_list(self, client: Client, meeting_id: int) -> None:
        """Todos returns a list of Todo models."""
        todos = client.meeting.todos(meeting_id)
        assert isinstance(todos, list)
        for t in todos:
            assert isinstance(t, Todo)

    def test_todos_include_closed(self, client: Client, meeting_id: int) -> None:
        """Todos with include_closed does not raise."""
        todos = client.meeting.todos(meeting_id, include_closed=True)
        assert isinstance(todos, list)


@pytest.mark.integration
class TestMeetingMetrics:
    """Tests for meeting.metrics()."""

    def test_metrics_returns_list(self, client: Client, meeting_id: int) -> None:
        """Metrics returns a list (possibly empty)."""
        metrics = client.meeting.metrics(meeting_id)
        assert isinstance(metrics, list)


@pytest.mark.integration
class TestMeetingDetails:
    """Tests for meeting.details()."""

    def test_details_returns_meeting_details(
        self, client: Client, meeting_id: int
    ) -> None:
        """Details returns a fully populated MeetingDetails."""
        details = client.meeting.details(meeting_id)
        assert isinstance(details, MeetingDetails)
        assert details.id == meeting_id
        assert isinstance(details.name, str)
        assert details.attendees is not None

    def test_details_nonexistent_meeting_raises(self, client: Client) -> None:
        """Details for a non-existent meeting ID raises an HTTP error."""
        import httpx

        with pytest.raises(httpx.HTTPStatusError):
            client.meeting.details(999999999)

    def test_details_populates_created_date(
        self, client: Client, meeting_id: int
    ) -> None:
        """Verify that details() populates created_date from the direct endpoint.

        Previously details() used getattr on MeetingListItem which never had
        these fields, so they were always None. Now it calls L10/{id} directly.
        """
        details = client.meeting.details(meeting_id)

        # created_date should be populated from the direct endpoint's CreateTime
        assert details.created_date is not None, (
            "created_date should be populated from the L10/{id} endpoint"
        )

    def test_details_works_for_non_attendee_meetings(self, client: Client) -> None:
        """Verify details() works even when user is not an attendee.

        Previously details() called self.list() which only returned meetings
        the user attended. Now it uses the direct L10/{id} endpoint.
        """
        # Create a meeting without adding self as attendee
        result = client.meeting.create("Fix Test - Not My Meeting", add_self=False)
        created_id = result["meeting_id"]

        try:
            # details() should now succeed even though we're not an attendee
            details = client.meeting.details(created_id)
            assert details.id == created_id
            assert details.name == "Fix Test - Not My Meeting"
        finally:
            client.meeting.delete(created_id)

    @pytest.mark.asyncio
    async def test_async_details(
        self, async_client: AsyncClient, meeting_id: int
    ) -> None:
        """Async details returns the same structure."""
        async with async_client:
            details = await async_client.meeting.details(meeting_id)
            assert isinstance(details, MeetingDetails)
            assert details.id == meeting_id


@pytest.mark.integration
class TestMeetingCreateDelete:
    """Tests for meeting create/delete lifecycle."""

    def test_create_and_delete(self, client: Client) -> None:
        """Create a meeting and then delete it."""
        result = client.meeting.create("Integration Create Test")
        assert "meeting_id" in result
        assert result["title"] == "Integration Create Test"
        assert isinstance(result["meeting_id"], int)

        # Verify it appears in list
        meetings = client.meeting.list()
        ids = [m.id for m in meetings]
        assert result["meeting_id"] in ids

        # Delete
        deleted = client.meeting.delete(result["meeting_id"])
        assert deleted is True

        # Verify it no longer appears
        meetings = client.meeting.list()
        ids = [m.id for m in meetings]
        assert result["meeting_id"] not in ids

    def test_create_with_add_self_false(self, client: Client) -> None:
        """Create a meeting with add_self=False."""
        result = client.meeting.create("No Self Meeting", add_self=False)
        mid = result["meeting_id"]

        try:
            # Meeting should NOT appear in our list
            meetings = client.meeting.list()
            ids = [m.id for m in meetings]
            assert mid not in ids
        finally:
            client.meeting.delete(mid)

    @pytest.mark.asyncio
    async def test_async_create_and_delete(self, async_client: AsyncClient) -> None:
        """Async create and delete lifecycle."""
        async with async_client:
            result = await async_client.meeting.create("Async Integration Test")
            assert "meeting_id" in result

            deleted = await async_client.meeting.delete(result["meeting_id"])
            assert deleted is True
