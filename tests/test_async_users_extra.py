"""Additional tests for async user operations to improve coverage."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import UserDetails, UserListItem


class TestAsyncUserOperationsExtra:
    """Additional test cases for AsyncUserOperations."""

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
        return client

    @pytest.mark.asyncio
    async def test_details_with_positions(
        self,
        async_client: AsyncClient,
        mock_async_client: AsyncMock,
    ) -> None:
        """Test fetching user details with positions."""
        # Mock the user details response
        user_data = {
            "Id": 123,
            "Name": "John Doe",
            "Description": "CEO",
            "Email": "john@example.com",
            "OrganizationId": 1,
            "ImageUrl": "https://example.com/avatar.jpg",
        }

        # Mock positions response
        positions_data = [
            {"Group": {"Position": {"Id": 1, "Name": "CEO"}}},
            {"Group": {"Position": {"Id": 2, "Name": "Board Member"}}},
        ]

        mock_user_response = MagicMock()
        mock_user_response.json.return_value = user_data
        mock_user_response.raise_for_status = MagicMock()

        mock_positions_response = MagicMock()
        mock_positions_response.json.return_value = positions_data
        mock_positions_response.raise_for_status = MagicMock()

        # Set up mock to return different responses
        def get_side_effect(url: str) -> MagicMock:
            if url == "users/123":
                return mock_user_response
            elif url == "users/123/seats":
                return mock_positions_response
            else:
                raise ValueError(f"Unexpected URL: {url}")

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        result = await async_client.user.details(user_id=123, include_positions=True)

        # Verify the result
        assert isinstance(result, UserDetails)
        assert result.id == 123
        assert result.positions is not None
        assert len(result.positions) == 2
        assert result.positions[0].name == "CEO"

    @pytest.mark.asyncio
    async def test_details_with_direct_reports(
        self,
        async_client: AsyncClient,
        mock_async_client: AsyncMock,
    ) -> None:
        """Test fetching user details with direct reports."""
        # Mock the user details response
        user_data = {
            "Id": 123,
            "Name": "John Doe",
            "Description": "CEO",
            "Email": "john@example.com",
            "OrganizationId": 1,
            "ImageUrl": "https://example.com/avatar.jpg",
        }

        # Mock direct reports response
        reports_data = [
            {
                "Id": 456,
                "Name": "Jane Smith",
                "Description": "VP Sales",
                "Email": "jane@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/jane.jpg",
            },
            {
                "Id": 789,
                "Name": "Bob Johnson",
                "Description": "VP Engineering",
                "Email": "bob@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/bob.jpg",
            },
        ]

        mock_user_response = MagicMock()
        mock_user_response.json.return_value = user_data
        mock_user_response.raise_for_status = MagicMock()

        mock_reports_response = MagicMock()
        mock_reports_response.json.return_value = reports_data
        mock_reports_response.raise_for_status = MagicMock()

        # Set up mock to return different responses
        def get_side_effect(url: str) -> MagicMock:
            if url == "users/123":
                return mock_user_response
            elif url == "users/123/directreports":
                return mock_reports_response
            else:
                raise ValueError(f"Unexpected URL: {url}")

        mock_async_client.get.side_effect = get_side_effect

        # Call the method
        result = await async_client.user.details(
            user_id=123, include_direct_reports=True
        )

        # Verify the result
        assert isinstance(result, UserDetails)
        assert result.id == 123
        assert result.direct_reports is not None
        assert len(result.direct_reports) == 2
        assert result.direct_reports[0].name == "Jane Smith"

    @pytest.mark.asyncio
    async def test_list_users(
        self,
        async_client: AsyncClient,
        mock_async_client: AsyncMock,
    ) -> None:
        """Test retrieving all users."""
        # Mock the response data
        users_data = [
            {
                "Id": 1,
                "Name": "User 1",
                "Description": "Title 1",
                "Email": "user1@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/user1.jpg",
                "ResultType": "User",
            },
            {
                "Id": 2,
                "Name": "User 2",
                "Description": "Title 2",
                "Email": "user2@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/user2.jpg",
                "ResultType": "User",
            },
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = users_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        # Call the method
        result = await async_client.user.list()

        # Verify the result
        assert len(result) == 2
        assert all(isinstance(user, UserListItem) for user in result)
        assert result[0].id == 1
        assert result[0].name == "User 1"

        # Verify the API call
        mock_async_client.get.assert_called_once_with(
            "search/all", params={"term": "%"}
        )
