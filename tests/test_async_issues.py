"""Tests for async issue operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import CreatedIssue, IssueDetails, IssueListItem


class TestAsyncIssueOperations:
    """Test async issue operations."""

    @pytest.fixture
    def mock_async_client(self) -> AsyncMock:
        """Create a mock async HTTP client.

        Returns:
            A mock async HTTP client.

        """
        mock = AsyncMock()
        mock.headers = {"Authorization": "Bearer test-api-key"}
        return mock

    @pytest_asyncio.fixture
    async def async_client(self, mock_async_client: AsyncMock) -> AsyncClient:
        """Create an AsyncClient with mocked HTTP client.

        Returns:
            An AsyncClient instance with mocked HTTP client.

        """
        client = AsyncClient(api_key="test-api-key")
        await client.close()  # Close the real client
        client._client = mock_async_client  # type: ignore[assignment]
        # Also update the operations to use the mocked client
        client.user._client = mock_async_client  # type: ignore[assignment]
        client.meeting._client = mock_async_client  # type: ignore[assignment]
        client.todo._client = mock_async_client  # type: ignore[assignment]
        client.issue._client = mock_async_client  # type: ignore[assignment]
        # Mock the user ID for operations
        client.issue._user_id = 123
        return client

    @pytest.mark.asyncio
    async def test_details(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test getting issue details."""
        mock_data = {
            "Id": 401,
            "Name": "Server performance issue",
            "DetailsUrl": "https://example.com/issue/401",
            "CreateTime": "2024-06-01T10:00:00Z",
            "CloseTime": None,
            "OriginId": 456,
            "Origin": "Infrastructure Meeting",
            "Owner": {"Id": 123, "Name": "John Doe"},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        issue = await async_client.issue.details(401)

        assert isinstance(issue, IssueDetails)
        assert issue.id == 401
        assert issue.title == "Server performance issue"
        assert issue.meeting_id == 456
        assert issue.user_name == "John Doe"
        assert issue.completed_at is None

        mock_async_client.get.assert_called_once_with("issues/401")

    @pytest.mark.asyncio
    async def test_list_by_user(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing issues by user."""
        mock_data = [
            {
                "Id": 401,
                "Name": "First issue",
                "DetailsUrl": "https://example.com/issue/401",
                "CreateTime": "2024-06-01T10:00:00Z",
                "OriginId": 456,
                "Origin": "Infrastructure Meeting",
            },
            {
                "Id": 402,
                "Name": "Second issue",
                "DetailsUrl": "https://example.com/issue/402",
                "CreateTime": "2024-06-02T10:00:00Z",
                "OriginId": 457,
                "Origin": "Product Meeting",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        issues = await async_client.issue.list()

        assert len(issues) == 2
        assert isinstance(issues[0], IssueListItem)
        assert issues[0].id == 401
        assert issues[0].title == "First issue"
        assert issues[1].meeting_title == "Product Meeting"

        mock_async_client.get.assert_called_once_with("issues/users/123")

    @pytest.mark.asyncio
    async def test_list_by_meeting(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing issues by meeting."""
        mock_data = [
            {
                "Id": 401,
                "Name": "Meeting issue",
                "DetailsUrl": "https://example.com/issue/401",
                "CreateTime": "2024-06-01T10:00:00Z",
                "OriginId": 456,
                "Origin": "Infrastructure Meeting",
            }
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        issues = await async_client.issue.list(meeting_id=456)

        assert len(issues) == 1
        assert issues[0].title == "Meeting issue"

        mock_async_client.get.assert_called_once_with("l10/456/issues")

    @pytest.mark.asyncio
    async def test_list_invalid_params(self, async_client: AsyncClient):
        """Test listing issues with both user_id and meeting_id raises error."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.issue.list(user_id=123, meeting_id=456)

    @pytest.mark.asyncio
    async def test_solve(self, async_client: AsyncClient, mock_async_client: AsyncMock):
        """Test solving an issue."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_async_client.post.return_value = mock_response

        result = await async_client.issue.solve(401)

        assert result is True
        mock_async_client.post.assert_called_once_with(
            "issues/401/complete", json={"complete": True}
        )

    @pytest.mark.asyncio
    async def test_create(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test creating a new issue."""
        mock_response_data = {
            "Id": 403,
            "Name": "New issue",
            "DetailsUrl": "https://example.com/issue/403",
            "OriginId": 456,
            "Origin": "Infrastructure Meeting",
            "Owner": {"Id": 123},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_response

        issue = await async_client.issue.create(
            meeting_id=456, title="New issue", notes="This needs urgent attention"
        )

        assert isinstance(issue, CreatedIssue)
        assert issue.id == 403
        assert issue.title == "New issue"
        assert issue.meeting_id == 456
        assert issue.user_id == 123

        mock_async_client.post.assert_called_once_with(
            "issues/create",
            json={
                "title": "New issue",
                "meetingid": 456,
                "ownerid": 123,
                "notes": "This needs urgent attention",
            },
        )

    @pytest.mark.asyncio
    async def test_create_without_notes(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test creating a new issue without notes."""
        mock_response_data = {
            "Id": 403,
            "Name": "New issue",
            "DetailsUrl": "https://example.com/issue/403",
            "OriginId": 456,
            "Origin": "Infrastructure Meeting",
            "Owner": {"Id": 123},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.post.return_value = mock_response

        issue = await async_client.issue.create(meeting_id=456, title="New issue")

        assert issue.id == 403

        mock_async_client.post.assert_called_once_with(
            "issues/create",
            json={"title": "New issue", "meetingid": 456, "ownerid": 123},
        )
