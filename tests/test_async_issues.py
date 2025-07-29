"""Tests for async issue operations."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import CreatedIssue


class TestAsyncIssueOperations:
    """Test cases for AsyncIssueOperations."""

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
        client.issue._client = mock_async_client  # type: ignore[assignment]
        return client

    @pytest.mark.asyncio
    async def test_create_many_all_successful(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where all issues are created successfully."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock create responses for each issue
        created_issues = [
            {
                "Id": 100,
                "Name": "Issue 1",
                "OriginId": 125,
                "Origin": "Team Meeting",
                "Owner": {"Id": 456, "Name": "John Doe"},
                "DetailsUrl": "https://example.com/issue/100",
            },
            {
                "Id": 101,
                "Name": "Issue 2",
                "OriginId": 125,
                "Origin": "Team Meeting",
                "Owner": {"Id": 789, "Name": "Jane Smith"},
                "DetailsUrl": "https://example.com/issue/101",
            },
            {
                "Id": 102,
                "Name": "Issue 3",
                "OriginId": 126,
                "Origin": "Planning Meeting",
                "Owner": {"Id": 456, "Name": "John Doe"},
                "DetailsUrl": "https://example.com/issue/102",
            },
        ]

        # Create mock responses for each issue
        mock_create_responses = []
        for issue_data in created_issues:
            mock_response = MagicMock()
            mock_response.json.return_value = issue_data
            mock_response.raise_for_status = MagicMock()
            mock_create_responses.append(mock_response)

        # Set up side effects
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.side_effect = mock_create_responses

        # Test data
        issues_to_create = [
            {"meeting_id": 125, "title": "Issue 1", "notes": "First issue"},
            {"meeting_id": 125, "title": "Issue 2", "user_id": 789},
            {"meeting_id": 126, "title": "Issue 3"},
        ]

        # Call the method
        result = await async_client.issue.create_many(issues_to_create)

        # Verify the result
        assert len(result.successful) == 3
        assert len(result.failed) == 0
        assert all(isinstance(issue, CreatedIssue) for issue in result.successful)
        assert result.successful[0].id == 100
        assert result.successful[1].id == 101
        assert result.successful[2].id == 102

        # Verify API calls - should be 1 get for user ID + 3 posts for issues
        assert mock_async_client.get.call_count == 1
        assert mock_async_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_create_many_partial_failure(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation where some issues fail."""
        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock responses - 1st succeeds, 2nd fails with 400, 3rd fails with 500
        mock_success_response = MagicMock()
        mock_success_response.json.return_value = {
            "Id": 200,
            "Name": "Success Issue",
            "OriginId": 125,
            "Origin": "Team Meeting",
            "Owner": {"Id": 456, "Name": "John Doe"},
            "DetailsUrl": "https://example.com/issue/200",
        }
        mock_success_response.raise_for_status = MagicMock()

        # Create error responses
        from httpx import HTTPStatusError, Response

        mock_400_response = Response(400, json={"error": "Bad Request"})
        mock_400_error = HTTPStatusError(
            "Bad Request", request=None, response=mock_400_response
        )

        mock_500_response = Response(500, json={"error": "Internal Server Error"})
        mock_500_error = HTTPStatusError(
            "Internal Server Error", request=None, response=mock_500_response
        )

        # Set up side effects
        mock_async_client.get.return_value = mock_user_response

        # Create side effect function that tracks call count
        call_count = 0

        def post_side_effect(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_success_response
            elif call_count == 2:
                # For 400 error, raise_for_status will throw
                mock_resp = MagicMock()
                mock_resp.raise_for_status.side_effect = mock_400_error
                return mock_resp
            else:
                # For 500 error, raise_for_status will throw
                mock_resp = MagicMock()
                mock_resp.raise_for_status.side_effect = mock_500_error
                return mock_resp

        mock_async_client.post.side_effect = post_side_effect

        # Test data
        issues_to_create = [
            {"meeting_id": 125, "title": "Success Issue"},
            {"meeting_id": 125, "title": "Bad Request Issue"},
            {"meeting_id": 126, "title": "Server Error Issue"},
        ]

        # Call the method
        result = await async_client.issue.create_many(issues_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.successful[0].id == 200
        assert result.successful[0].title == "Success Issue"

        # Check failed items
        assert result.failed[0].index == 1
        assert result.failed[0].input_data == issues_to_create[1]
        assert "Bad Request" in result.failed[0].error

        assert result.failed[1].index == 2
        assert result.failed[1].input_data == issues_to_create[2]
        assert "Internal Server Error" in result.failed[1].error

    @pytest.mark.asyncio
    async def test_create_many_empty_list(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with an empty list."""
        # Call the method with empty list
        result = await async_client.issue.create_many([])

        # Verify the result
        assert len(result.successful) == 0
        assert len(result.failed) == 0

        # Verify no API calls were made
        mock_async_client.get.assert_not_called()
        mock_async_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_many_validation_errors(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test bulk creation with validation errors (missing required fields)."""
        # Test data with missing required fields
        issues_to_create = [
            {"meeting_id": 125, "title": "Valid Issue"},  # Valid
            {"title": "Missing Meeting ID"},  # Missing meeting_id
            {"meeting_id": 125},  # Missing title
            {},  # Missing both required fields
        ]

        # Mock user ID response for valid issue
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Mock successful create response for valid issue
        mock_create_response = MagicMock()
        mock_create_response.json.return_value = {
            "Id": 300,
            "Name": "Valid Issue",
            "OriginId": 125,
            "Origin": "Team Meeting",
            "Owner": {"Id": 456, "Name": "John Doe"},
            "DetailsUrl": "https://example.com/issue/300",
        }
        mock_create_response.raise_for_status = MagicMock()

        # Set up mocks
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.return_value = mock_create_response

        # Call the method
        result = await async_client.issue.create_many(issues_to_create)

        # Verify the result
        assert len(result.successful) == 1
        assert len(result.failed) == 3
        assert result.successful[0].id == 300

        # Check validation errors
        assert result.failed[0].index == 1
        assert "meeting_id is required" in result.failed[0].error

        assert result.failed[1].index == 2
        assert "title is required" in result.failed[1].error

        assert result.failed[2].index == 3
        assert "meeting_id is required" in result.failed[2].error

        # Only one successful creation should have been attempted
        assert mock_async_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_create_many_concurrent_execution(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ) -> None:
        """Test that create_many executes operations concurrently."""
        import time

        # Mock user ID response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {"Id": 456}
        mock_user_response.raise_for_status = MagicMock()

        # Track when each call starts and ends
        call_times = []

        async def delayed_post(*_args, **_kwargs):
            """Simulate a network call with delay.

            Returns:
                Mock response object.

            """
            start_time = time.time()
            await asyncio.sleep(0.1)  # Simulate network delay
            end_time = time.time()
            call_times.append((start_time, end_time))

            # Return a mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "Id": len(call_times) + 400,
                "Name": f"Issue {len(call_times)}",
                "OriginId": 125,
                "Origin": "Team Meeting",
                "Owner": {"Id": 456, "Name": "John Doe"},
                "DetailsUrl": f"https://example.com/issue/{len(call_times) + 400}",
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response

        # Set up mocks
        mock_async_client.get.return_value = mock_user_response
        mock_async_client.post.side_effect = delayed_post

        # Create multiple issues
        issues_to_create = [
            {"meeting_id": 125, "title": f"Issue {i}"} for i in range(5)
        ]

        # Call the method with max_concurrent=3
        start_time = time.time()
        result = await async_client.issue.create_many(
            issues_to_create, max_concurrent=3
        )
        total_time = time.time() - start_time

        # Verify all were successful
        assert len(result.successful) == 5
        assert len(result.failed) == 0

        # Verify concurrent execution
        # With max_concurrent=3 and 5 issues with 0.1s delay each:
        # - First 3 should start almost simultaneously
        # - Next 2 should start after first ones complete
        # Total time should be ~0.2s (2 batches) not ~0.5s (sequential)
        assert total_time < 0.3  # Allow some overhead

        # Check that we had overlapping executions
        overlapping_count = 0
        for i in range(len(call_times) - 1):
            for j in range(i + 1, len(call_times)):
                # Check if execution times overlap
                if (
                    call_times[i][0] < call_times[j][1]
                    and call_times[j][0] < call_times[i][1]
                ):
                    overlapping_count += 1

        assert overlapping_count > 0  # Confirm concurrent execution
