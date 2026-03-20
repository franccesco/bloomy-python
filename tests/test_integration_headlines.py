"""Integration tests for Headline operations against the real Bloom Growth API."""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

from bloomy import AsyncClient, Client
from bloomy.models import HeadlineDetails, HeadlineInfo, HeadlineListItem

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


class TestHeadlineLifecycleSync:
    """Full CRUD lifecycle tests for sync headline operations."""

    def test_create_headline(self, client: Client) -> None:
        """Test creating a headline via the real API."""
        tag = uuid.uuid4().hex[:8]
        title = f"Integration test headline {tag}"
        result = client.headline.create(meeting_id=MEETING_ID, title=title)

        assert isinstance(result, HeadlineInfo)
        assert result.id > 0
        assert result.title == title
        assert result.owner_details.id > 0

        # Cleanup
        client.headline.delete(result.id)

    def test_create_headline_with_notes(self, client: Client) -> None:
        """Test creating a headline with notes."""
        tag = uuid.uuid4().hex[:8]
        title = f"Integration test headline notes {tag}"
        result = client.headline.create(
            meeting_id=MEETING_ID,
            title=title,
            notes="Some integration test notes",
        )

        assert isinstance(result, HeadlineInfo)
        assert result.title == title

        # Cleanup
        client.headline.delete(result.id)

    def test_headline_details(self, client: Client) -> None:
        """Test retrieving headline details."""
        tag = uuid.uuid4().hex[:8]
        created = client.headline.create(
            meeting_id=MEETING_ID, title=f"Detail test headline {tag}"
        )

        details = client.headline.details(created.id)

        assert isinstance(details, HeadlineDetails)
        assert details.id == created.id
        assert details.title == created.title
        assert details.meeting_details.id == MEETING_ID

        # Cleanup
        client.headline.delete(created.id)

    def test_headline_update(self, client: Client) -> None:
        """Test updating a headline."""
        tag = uuid.uuid4().hex[:8]
        created = client.headline.create(
            meeting_id=MEETING_ID, title=f"Update test headline {tag}"
        )

        updated_title = f"Updated headline {tag}"
        # update returns None
        client.headline.update(created.id, title=updated_title)

        # Verify the update by fetching details
        details = client.headline.details(created.id)
        assert details.title == updated_title

        # Cleanup
        client.headline.delete(created.id)

    def test_headline_delete(self, client: Client) -> None:
        """Test deleting a headline."""
        tag = uuid.uuid4().hex[:8]
        created = client.headline.create(
            meeting_id=MEETING_ID, title=f"Delete test headline {tag}"
        )

        # Delete should not raise
        client.headline.delete(created.id)

    def test_list_user_headlines(self, client: Client) -> None:
        """Test listing headlines for the current user."""
        result = client.headline.list()

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, HeadlineListItem)

    def test_list_meeting_headlines(self, client: Client) -> None:
        """Test listing headlines for a meeting."""
        result = client.headline.list(meeting_id=MEETING_ID)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, HeadlineListItem)

    def test_list_specific_user_headlines(self, client: Client) -> None:
        """Test listing headlines for a specific user by ID."""
        user_id = client.user.details().id
        result = client.headline.list(user_id=user_id)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, HeadlineListItem)

    def test_list_both_params_raises(self, client: Client) -> None:
        """Test that providing both user_id and meeting_id raises ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            client.headline.list(user_id=123, meeting_id=456)

    def test_list_truthiness_bug_zero_user_id(self, client: Client) -> None:
        """Test that user_id=0 with meeting_id raises ValueError.

        BUG: `if user_id and meeting_id` fails when user_id=0 because
        0 is falsy. Should use `is not None` checks instead.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            client.headline.list(user_id=0, meeting_id=MEETING_ID)

    def test_list_truthiness_bug_zero_meeting_id(self, client: Client) -> None:
        """Test that meeting_id=0 with user_id raises ValueError.

        BUG: `if user_id and meeting_id` fails when meeting_id=0 because
        0 is falsy. Should use `is not None` checks instead.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            client.headline.list(user_id=123, meeting_id=0)

    def test_full_lifecycle(self, client: Client) -> None:
        """Test complete headline lifecycle: create -> details -> update -> delete."""
        tag = uuid.uuid4().hex[:8]

        # Create
        created = client.headline.create(
            meeting_id=MEETING_ID,
            title=f"Lifecycle headline {tag}",
            notes="Lifecycle test notes",
        )
        assert created.id > 0

        # Details
        details = client.headline.details(created.id)
        assert details.id == created.id
        assert details.archived is False

        # Update
        new_title = f"Updated lifecycle headline {tag}"
        client.headline.update(created.id, title=new_title)
        updated_details = client.headline.details(created.id)
        assert updated_details.title == new_title

        # Delete
        client.headline.delete(created.id)


class TestHeadlineLifecycleAsync:
    """Full CRUD lifecycle tests for async headline operations."""

    @pytest.mark.asyncio
    async def test_create_headline(self, async_client: AsyncClient) -> None:
        """Test creating a headline via the async API."""
        tag = uuid.uuid4().hex[:8]
        title = f"Async integration test headline {tag}"
        result = await async_client.headline.create(meeting_id=MEETING_ID, title=title)

        assert isinstance(result, HeadlineInfo)
        assert result.id > 0
        assert result.title == title

        # Cleanup
        await async_client.headline.delete(result.id)

    @pytest.mark.asyncio
    async def test_headline_details(self, async_client: AsyncClient) -> None:
        """Test retrieving headline details via async API."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.headline.create(
            meeting_id=MEETING_ID, title=f"Async detail test {tag}"
        )

        details = await async_client.headline.details(created.id)

        assert isinstance(details, HeadlineDetails)
        assert details.id == created.id

        # Cleanup
        await async_client.headline.delete(created.id)

    @pytest.mark.asyncio
    async def test_headline_update(self, async_client: AsyncClient) -> None:
        """Test updating a headline via async API."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.headline.create(
            meeting_id=MEETING_ID, title=f"Async update test {tag}"
        )

        updated_title = f"Async updated {tag}"
        await async_client.headline.update(created.id, title=updated_title)

        details = await async_client.headline.details(created.id)
        assert details.title == updated_title

        # Cleanup
        await async_client.headline.delete(created.id)

    @pytest.mark.asyncio
    async def test_headline_delete(self, async_client: AsyncClient) -> None:
        """Test deleting a headline via async API."""
        tag = uuid.uuid4().hex[:8]
        created = await async_client.headline.create(
            meeting_id=MEETING_ID, title=f"Async delete test {tag}"
        )

        await async_client.headline.delete(created.id)

    @pytest.mark.asyncio
    async def test_list_user_headlines(self, async_client: AsyncClient) -> None:
        """Test listing headlines for the current user via async API."""
        result = await async_client.headline.list()

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, HeadlineListItem)

    @pytest.mark.asyncio
    async def test_list_meeting_headlines(self, async_client: AsyncClient) -> None:
        """Test listing headlines for a meeting via async API."""
        result = await async_client.headline.list(meeting_id=MEETING_ID)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, HeadlineListItem)

    @pytest.mark.asyncio
    async def test_list_both_params_raises(self, async_client: AsyncClient) -> None:
        """Test that providing both params raises ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.headline.list(user_id=123, meeting_id=456)

    @pytest.mark.asyncio
    async def test_list_truthiness_bug_zero_user_id(
        self, async_client: AsyncClient
    ) -> None:
        """Test truthiness bug: user_id=0 with meeting_id should raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.headline.list(user_id=0, meeting_id=MEETING_ID)

    @pytest.mark.asyncio
    async def test_list_truthiness_bug_zero_meeting_id(
        self, async_client: AsyncClient
    ) -> None:
        """Test truthiness bug: meeting_id=0 with user_id should raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.headline.list(user_id=123, meeting_id=0)

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, async_client: AsyncClient) -> None:
        """Test complete async headline lifecycle."""
        tag = uuid.uuid4().hex[:8]

        # Create
        created = await async_client.headline.create(
            meeting_id=MEETING_ID,
            title=f"Async lifecycle {tag}",
            notes="Async lifecycle notes",
        )
        assert created.id > 0

        # Details
        details = await async_client.headline.details(created.id)
        assert details.id == created.id

        # Update
        new_title = f"Async updated lifecycle {tag}"
        await async_client.headline.update(created.id, title=new_title)
        updated_details = await async_client.headline.details(created.id)
        assert updated_details.title == new_title

        # Delete
        await async_client.headline.delete(created.id)
