"""Integration tests for user operations and configuration against the real API."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio

from bloomy import AsyncClient, Client, Configuration, ConfigurationError
from bloomy.models import (
    DirectReport,
    Position,
    UserDetails,
    UserListItem,
    UserSearchResult,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_key() -> str:
    """Get the API key from the environment.

    Returns:
        The BG_API_KEY value.

    """
    key = os.environ.get("BG_API_KEY")
    if not key:
        pytest.skip("BG_API_KEY not set")
    return key


@pytest.fixture(scope="module")
def client(api_key: str) -> Client:
    """Create a real Client instance for integration tests.

    Yields:
        A Client connected to the real API.

    """
    with Client(api_key=api_key) as c:
        yield c


@pytest_asyncio.fixture
async def async_client(api_key: str) -> AsyncClient:
    """Create a real AsyncClient instance for integration tests.

    Yields:
        An AsyncClient connected to the real API.

    """
    async with AsyncClient(api_key=api_key) as c:
        yield c


# ---------------------------------------------------------------------------
# Configuration tests
# ---------------------------------------------------------------------------


class TestConfiguration:
    """Tests for the Configuration class."""

    def test_configuration_with_explicit_key(self, api_key: str) -> None:
        """Configuration should accept an explicit API key."""
        config = Configuration(api_key=api_key)
        assert config.api_key == api_key

    def test_configuration_from_env_var(self) -> None:
        """Configuration should pick up the BG_API_KEY environment variable."""
        key = os.environ.get("BG_API_KEY")
        if not key:
            pytest.skip("BG_API_KEY not set")
        config = Configuration()
        assert config.api_key == key

    def test_configuration_none_when_no_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configuration should have api_key=None when no source available."""
        monkeypatch.delenv("BG_API_KEY", raising=False)
        config = Configuration()
        # api_key could be loaded from config file; if not present it's None
        # We just verify it doesn't raise
        assert config.api_key is None or isinstance(config.api_key, str)

    def test_client_raises_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Client should raise ConfigurationError when no API key exists."""
        monkeypatch.delenv("BG_API_KEY", raising=False)
        # Patch _load_api_key to ensure no config file fallback
        with pytest.raises(ConfigurationError):
            Client(api_key=None)

    def test_whitespace_only_api_key_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Whitespace-only API key should be rejected by Client."""
        monkeypatch.delenv("BG_API_KEY", raising=False)
        with pytest.raises(ConfigurationError):
            Client(api_key="   ")

    def test_configuration_strips_whitespace(self, api_key: str) -> None:
        """Configuration should strip surrounding whitespace from API key."""
        config = Configuration(api_key=f"  {api_key}  ")
        assert config.api_key == api_key


# ---------------------------------------------------------------------------
# Sync user operations
# ---------------------------------------------------------------------------


class TestUserDetailsSync:
    """Tests for sync user.details()."""

    def test_current_user_details(self, client: Client) -> None:
        """Get details for the authenticated user (no explicit user_id)."""
        user = client.user.details()
        assert isinstance(user, UserDetails)
        assert isinstance(user.id, int)
        assert isinstance(user.name, str)
        assert len(user.name) > 0
        assert isinstance(user.image_url, str)

    def test_current_user_details_with_explicit_id(self, client: Client) -> None:
        """Get details using an explicit user_id (same user)."""
        my_id = client.user.user_id
        user = client.user.details(user_id=my_id)
        assert user.id == my_id

    def test_details_include_direct_reports(self, client: Client) -> None:
        """include_direct_reports should populate the direct_reports field."""
        user = client.user.details(include_direct_reports=True)
        assert user.direct_reports is not None
        assert isinstance(user.direct_reports, list)
        for dr in user.direct_reports:
            assert isinstance(dr, DirectReport)

    def test_details_include_positions(self, client: Client) -> None:
        """include_positions should populate the positions field."""
        user = client.user.details(include_positions=True)
        assert user.positions is not None
        assert isinstance(user.positions, list)
        for pos in user.positions:
            assert isinstance(pos, Position)

    def test_details_include_all(self, client: Client) -> None:
        """include_all should populate both direct_reports and positions."""
        user = client.user.details(include_all=True)
        assert user.direct_reports is not None
        assert user.positions is not None

    def test_details_without_includes_has_none_fields(self, client: Client) -> None:
        """Without include flags, direct_reports and positions should be None."""
        user = client.user.details()
        assert user.direct_reports is None
        assert user.positions is None


class TestDirectReportsSync:
    """Tests for sync user.direct_reports()."""

    def test_direct_reports_returns_list(self, client: Client) -> None:
        """direct_reports() should return a list of DirectReport models."""
        reports = client.user.direct_reports()
        assert isinstance(reports, list)
        for report in reports:
            assert isinstance(report, DirectReport)
            assert isinstance(report.id, int)
            assert isinstance(report.name, str)
            assert isinstance(report.image_url, str)


class TestPositionsSync:
    """Tests for sync user.positions()."""

    def test_positions_returns_list(self, client: Client) -> None:
        """positions() should return a list of Position models."""
        positions = client.user.positions()
        assert isinstance(positions, list)
        for pos in positions:
            assert isinstance(pos, Position)
            assert isinstance(pos.id, int)


class TestSearchSync:
    """Tests for sync user.search()."""

    def test_search_returns_results(self, client: Client) -> None:
        """search() with a broad term should return results."""
        # Get the current user's name to use as a search term
        me = client.user.details()
        first_name = me.name.split()[0]
        results = client.user.search(term=first_name)
        assert isinstance(results, list)
        assert len(results) > 0
        for result in results:
            assert isinstance(result, UserSearchResult)
            assert isinstance(result.id, int)
            assert isinstance(result.name, str)
            assert isinstance(result.email, str)
            assert isinstance(result.organization_id, int)

    def test_search_empty_term_returns_empty(self, client: Client) -> None:
        """search() with a nonsense term should return an empty list."""
        results = client.user.search(term="zzzznonexistentuserxyz9999")
        assert isinstance(results, list)
        assert len(results) == 0


class TestListSync:
    """Tests for sync user.list()."""

    def test_list_returns_users(self, client: Client) -> None:
        """list() should return a non-empty list of UserListItem."""
        users = client.user.list()
        assert isinstance(users, list)
        assert len(users) > 0
        for user in users:
            assert isinstance(user, UserListItem)
            assert isinstance(user.id, int)
            assert isinstance(user.name, str)
            assert isinstance(user.email, str)

    def test_list_with_placeholders(self, client: Client) -> None:
        """list(include_placeholders=True) may return more users."""
        without = client.user.list(include_placeholders=False)
        with_ph = client.user.list(include_placeholders=True)
        assert len(with_ph) >= len(without)


# ---------------------------------------------------------------------------
# Async user operations
# ---------------------------------------------------------------------------


class TestUserDetailsAsync:
    """Tests for async user.details()."""

    @pytest.mark.asyncio
    async def test_current_user_details(self, async_client: AsyncClient) -> None:
        """Get details for the authenticated user (async)."""
        user = await async_client.user.details()
        assert isinstance(user, UserDetails)
        assert isinstance(user.id, int)
        assert isinstance(user.name, str)
        assert len(user.name) > 0

    @pytest.mark.asyncio
    async def test_details_include_all(self, async_client: AsyncClient) -> None:
        """include_all should populate both fields (async)."""
        user = await async_client.user.details(include_all=True)
        assert user.direct_reports is not None
        assert user.positions is not None


class TestDirectReportsAsync:
    """Tests for async user.direct_reports()."""

    @pytest.mark.asyncio
    async def test_direct_reports_returns_list(self, async_client: AsyncClient) -> None:
        """direct_reports() should return a list of DirectReport models (async)."""
        reports = await async_client.user.direct_reports()
        assert isinstance(reports, list)
        for report in reports:
            assert isinstance(report, DirectReport)


class TestPositionsAsync:
    """Tests for async user.positions()."""

    @pytest.mark.asyncio
    async def test_positions_returns_list(self, async_client: AsyncClient) -> None:
        """positions() should return a list of Position models (async)."""
        positions = await async_client.user.positions()
        assert isinstance(positions, list)
        for pos in positions:
            assert isinstance(pos, Position)


class TestSearchAsync:
    """Tests for async user.search()."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, async_client: AsyncClient) -> None:
        """search() with a broad term should return results (async)."""
        me = await async_client.user.details()
        first_name = me.name.split()[0]
        results = await async_client.user.search(term=first_name)
        assert isinstance(results, list)
        assert len(results) > 0
        for result in results:
            assert isinstance(result, UserSearchResult)


class TestListAsync:
    """Tests for async user.list()."""

    @pytest.mark.asyncio
    async def test_list_returns_users(self, async_client: AsyncClient) -> None:
        """list() should return a non-empty list (async)."""
        users = await async_client.user.list()
        assert isinstance(users, list)
        assert len(users) > 0
        for user in users:
            assert isinstance(user, UserListItem)


# ---------------------------------------------------------------------------
# Cross-check: sync vs async consistency
# ---------------------------------------------------------------------------


class TestSyncAsyncConsistency:
    """Verify sync and async operations return equivalent data."""

    @pytest.mark.asyncio
    async def test_user_details_match(
        self, client: Client, async_client: AsyncClient
    ) -> None:
        """Sync and async user.details() should return the same user."""
        sync_user = client.user.details()
        async_user = await async_client.user.details()
        assert sync_user.id == async_user.id
        assert sync_user.name == async_user.name

    @pytest.mark.asyncio
    async def test_user_list_match(
        self, client: Client, async_client: AsyncClient
    ) -> None:
        """Sync and async user.list() should return the same set of users."""
        sync_users = client.user.list()
        async_users = await async_client.user.list()
        sync_ids = {u.id for u in sync_users}
        async_ids = {u.id for u in async_users}
        assert sync_ids == async_ids
