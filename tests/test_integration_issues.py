"""Integration tests for Issue operations against the real Bloom Growth API."""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

from bloomy import AsyncClient, Client
from bloomy.models import CreatedIssue, IssueDetails, IssueListItem

MEETING_ID = 324926

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


class TestIssueLifecycleSync:
    """Full CRUD lifecycle tests for sync issue operations."""

    def test_create_issue(self, client: Client) -> None:
        """Test creating an issue via the real API."""
        tag = uuid.uuid4().hex[:8]
        title = f"Integration test issue {tag}"
        result = client.issue.create(meeting_id=MEETING_ID, title=title)

        assert isinstance(result, CreatedIssue)
        assert result.id > 0
        assert result.title == title
        assert result.meeting_id == MEETING_ID

        # Cleanup
        client.issue.complete(result.id)

    def test_create_issue_with_notes(self, client: Client) -> None:
        """Test creating an issue with notes."""
        tag = uuid.uuid4().hex[:8]
        title = f"Integration test issue notes {tag}"
        result = client.issue.create(
            meeting_id=MEETING_ID,
            title=title,
            notes="Some integration test notes",
        )

        assert isinstance(result, CreatedIssue)
        assert result.title == title

        # Cleanup
        client.issue.complete(result.id)

    def test_issue_details(self, client: Client) -> None:
        """Test retrieving issue details."""
        tag = uuid.uuid4().hex[:8]
        created = client.issue.create(
            meeting_id=MEETING_ID, title=f"Detail test issue {tag}"
        )

        details = client.issue.details(created.id)

        assert isinstance(details, IssueDetails)
        assert details.id == created.id
        assert details.title == created.title
        assert details.meeting_id == MEETING_ID

        # Cleanup
        client.issue.complete(created.id)

    def test_issue_update(self, client: Client) -> None:
        """Test updating an issue."""
        tag = uuid.uuid4().hex[:8]
        created = client.issue.create(
            meeting_id=MEETING_ID, title=f"Update test issue {tag}"
        )

        updated_title = f"Updated issue {tag}"
        updated = client.issue.update(created.id, title=updated_title)

        assert isinstance(updated, IssueDetails)
        assert updated.title == updated_title

        # Cleanup
        client.issue.complete(created.id)

    def test_issue_complete(self, client: Client) -> None:
        """Test completing an issue."""
        tag = uuid.uuid4().hex[:8]
        created = client.issue.create(
            meeting_id=MEETING_ID, title=f"Complete test issue {tag}"
        )

        completed = client.issue.complete(created.id)

        assert isinstance(completed, IssueDetails)
        assert completed.completed_at is not None

    def test_list_user_issues(self, client: Client) -> None:
        """Test listing issues for the current user."""
        result = client.issue.list()

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, IssueListItem)

    def test_list_meeting_issues(self, client: Client) -> None:
        """Test listing issues for a meeting."""
        result = client.issue.list(meeting_id=MEETING_ID)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, IssueListItem)

    def test_list_specific_user_issues(self, client: Client) -> None:
        """Test listing issues for a specific user by ID."""
        user_id = client.user.details().id
        result = client.issue.list(user_id=user_id)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, IssueListItem)

    def test_list_both_params_raises(self, client: Client) -> None:
        """Test that providing both user_id and meeting_id raises ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            client.issue.list(user_id=123, meeting_id=456)

    def test_list_truthiness_bug_zero_user_id(self, client: Client) -> None:
        """Test that user_id=0 with meeting_id raises ValueError.

        BUG: `if user_id and meeting_id` fails when user_id=0 because
        0 is falsy. Should use `is not None` checks instead.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            client.issue.list(user_id=0, meeting_id=MEETING_ID)

    def test_list_truthiness_bug_zero_meeting_id(self, client: Client) -> None:
        """Test that meeting_id=0 with user_id raises ValueError.

        BUG: `if user_id and meeting_id` fails when meeting_id=0 because
        0 is falsy. Should use `is not None` checks instead.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            client.issue.list(user_id=123, meeting_id=0)

    def test_full_lifecycle(self, client: Client) -> None:
        """Test complete issue lifecycle: create -> details -> update -> complete."""
        tag = uuid.uuid4().hex[:8]

        # Create
        created = client.issue.create(
            meeting_id=MEETING_ID,
            title=f"Lifecycle issue {tag}",
            notes="Lifecycle test notes",
        )
        assert created.id > 0

        # Details
        details = client.issue.details(created.id)
        assert details.id == created.id
        assert details.completed_at is None

        # Update
        new_title = f"Updated lifecycle issue {tag}"
        updated = client.issue.update(created.id, title=new_title)
        assert updated.title == new_title

        # Complete
        completed = client.issue.complete(created.id)
        assert completed.completed_at is not None


class TestIssueLifecycleAsync:
    """Full CRUD lifecycle tests for async issue operations."""

    @pytest.mark.asyncio
    async def test_create_issue(self, async_client: AsyncClient) -> None:
        """Test creating an issue via the async API."""
        tag = uuid.uuid4().hex[:8]
        title = f"Async integration test issue {tag}"
        result = await async_client.issue.create(meeting_id=MEETING_ID, title=title)

        assert isinstance(result, CreatedIssue)
        assert result.id > 0
        assert result.title == title

        # Cleanup
        await async_client.issue.complete(result.id)

    @pytest.mark.asyncio
    async def test_issue_details(self, async_client: AsyncClient) -> None:
        """Test retrieving issue details via async API."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.issue.create(
            meeting_id=MEETING_ID, title=f"Async detail test {tag}"
        )

        details = await async_client.issue.details(created.id)

        assert isinstance(details, IssueDetails)
        assert details.id == created.id

        # Cleanup
        await async_client.issue.complete(created.id)

    @pytest.mark.asyncio
    async def test_issue_update(self, async_client: AsyncClient) -> None:
        """Test updating an issue via async API."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.issue.create(
            meeting_id=MEETING_ID, title=f"Async update test {tag}"
        )

        updated_title = f"Async updated {tag}"
        updated = await async_client.issue.update(created.id, title=updated_title)

        assert updated.title == updated_title

        # Cleanup
        await async_client.issue.complete(created.id)

    @pytest.mark.asyncio
    async def test_issue_complete(self, async_client: AsyncClient) -> None:
        """Test completing an issue via async API."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.issue.create(
            meeting_id=MEETING_ID, title=f"Async complete test {tag}"
        )

        completed = await async_client.issue.complete(created.id)

        assert completed.completed_at is not None

    @pytest.mark.asyncio
    async def test_list_user_issues(self, async_client: AsyncClient) -> None:
        """Test listing issues for the current user via async API."""
        result = await async_client.issue.list()

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, IssueListItem)

    @pytest.mark.asyncio
    async def test_list_meeting_issues(self, async_client: AsyncClient) -> None:
        """Test listing issues for a meeting via async API."""
        result = await async_client.issue.list(meeting_id=MEETING_ID)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, IssueListItem)

    @pytest.mark.asyncio
    async def test_list_both_params_raises(self, async_client: AsyncClient) -> None:
        """Test that providing both params raises ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.issue.list(user_id=123, meeting_id=456)

    @pytest.mark.asyncio
    async def test_list_truthiness_bug_zero_user_id(
        self, async_client: AsyncClient
    ) -> None:
        """Test truthiness bug: user_id=0 with meeting_id should raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.issue.list(user_id=0, meeting_id=MEETING_ID)

    @pytest.mark.asyncio
    async def test_list_truthiness_bug_zero_meeting_id(
        self, async_client: AsyncClient
    ) -> None:
        """Test truthiness bug: meeting_id=0 with user_id should raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.issue.list(user_id=123, meeting_id=0)

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Test complete async issue lifecycle."""
        tag = uuid.uuid4().hex[:8]

        # Create
        created = await async_client.issue.create(
            meeting_id=MEETING_ID,
            title=f"Async lifecycle {tag}",
            notes="Async lifecycle notes",
        )
        assert created.id > 0

        # Details
        details = await async_client.issue.details(created.id)
        assert details.id == created.id

        # Update
        new_title = f"Async updated lifecycle {tag}"
        updated = await async_client.issue.update(created.id, title=new_title)
        assert updated.title == new_title

        # Complete
        completed = await async_client.issue.complete(created.id)
        assert completed.completed_at is not None
