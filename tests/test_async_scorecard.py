"""Tests for async scorecard operations."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from bloomy import AsyncClient
from bloomy.models import ScorecardItem, ScorecardWeek


class TestAsyncScorecardOperations:
    """Test async scorecard operations."""

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
        client.scorecard._client = mock_async_client  # type: ignore[assignment]
        # Mock the user ID for operations
        client.scorecard._user_id = 123
        return client

    @pytest.mark.asyncio
    async def test_current_week(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test getting current week details."""
        mock_data = {
            "Id": 2024,
            "ForWeekNumber": 24,
            "LocalDate": {"Date": "2024-06-10"},
            "ForWeek": "2024-06-16",
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        week = await async_client.scorecard.current_week()

        assert isinstance(week, ScorecardWeek)
        assert week.id == 2024
        assert week.week_number == 24
        assert week.week_start == "2024-06-10"
        assert week.week_end == "2024-06-16"

        mock_async_client.get.assert_called_once_with("weeks/current")

    @pytest.mark.asyncio
    async def test_list_by_user(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing scorecards by user."""
        mock_data = {
            "Scores": [
                {
                    "Id": 201,
                    "MeasurableId": 301,
                    "AccountableUserId": 123,
                    "MeasurableName": "Sales Revenue",
                    "Target": 100000,
                    "Measured": 95000,
                    "Week": "2024-W25",
                    "ForWeek": 25,
                    "DateEntered": "2024-06-20T10:00:00Z",
                },
                {
                    "Id": 202,
                    "MeasurableId": 302,
                    "AccountableUserId": 123,
                    "MeasurableName": "Customer Satisfaction",
                    "Target": 90,
                    "Measured": None,
                    "Week": "2024-W25",
                    "ForWeek": 25,
                    "DateEntered": "2024-06-20T10:00:00Z",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        scorecards = await async_client.scorecard.list()

        assert len(scorecards) == 1  # Only one with non-None value
        assert isinstance(scorecards[0], ScorecardItem)
        assert scorecards[0].id == 201
        assert scorecards[0].title == "Sales Revenue"
        assert scorecards[0].value == 95000

        mock_async_client.get.assert_called_once_with("scorecard/user/123")

    @pytest.mark.asyncio
    async def test_list_by_meeting(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing scorecards by meeting."""
        mock_data = {
            "Scores": [
                {
                    "Id": 201,
                    "MeasurableId": 301,
                    "AccountableUserId": 123,
                    "MeasurableName": "Team Productivity",
                    "Target": 100,
                    "Measured": 105,
                    "Week": "2024-W25",
                    "ForWeek": 25,
                    "DateEntered": "2024-06-20T10:00:00Z",
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        scorecards = await async_client.scorecard.list(meeting_id=456)

        assert len(scorecards) == 1
        assert scorecards[0].title == "Team Productivity"

        mock_async_client.get.assert_called_once_with("scorecard/meeting/456")

    @pytest.mark.asyncio
    async def test_list_show_empty(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing scorecards with show_empty=True."""
        mock_data = {
            "Scores": [
                {
                    "Id": 201,
                    "MeasurableId": 301,
                    "AccountableUserId": 123,
                    "MeasurableName": "Sales Revenue",
                    "Target": 100000,
                    "Measured": 95000,
                    "Week": "2024-W25",
                    "ForWeek": 25,
                    "DateEntered": "2024-06-20T10:00:00Z",
                },
                {
                    "Id": 202,
                    "MeasurableId": 302,
                    "AccountableUserId": 123,
                    "MeasurableName": "Customer Satisfaction",
                    "Target": 90,
                    "Measured": None,
                    "Week": "2024-W25",
                    "ForWeek": 25,
                    "DateEntered": "2024-06-20T10:00:00Z",
                },
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        mock_async_client.get.return_value = mock_response

        scorecards = await async_client.scorecard.list(show_empty=True)

        assert len(scorecards) == 2  # Both items included
        assert scorecards[1].value is None

    @pytest.mark.asyncio
    async def test_list_with_week_offset(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test listing scorecards with week offset."""
        # Mock current week response
        week_data = {
            "Id": 2024,
            "ForWeekNumber": 24,
            "LocalDate": {"Date": "2024-06-10"},
            "ForWeek": "2024-06-16",
        }

        # Mock scorecard data
        scorecard_data = {
            "Scores": [
                {
                    "Id": 201,
                    "MeasurableId": 301,
                    "AccountableUserId": 123,
                    "MeasurableName": "Sales Revenue",
                    "Target": 100000,
                    "Measured": 95000,
                    "Week": "2024-W23",
                    "ForWeek": 23,  # Previous week
                    "DateEntered": "2024-06-13T10:00:00Z",
                },
                {
                    "Id": 202,
                    "MeasurableId": 302,
                    "AccountableUserId": 123,
                    "MeasurableName": "Customer Satisfaction",
                    "Target": 90,
                    "Measured": 88,
                    "Week": "2024-W24",
                    "ForWeek": 24,  # Current week
                    "DateEntered": "2024-06-20T10:00:00Z",
                },
            ]
        }

        mock_response1 = MagicMock()
        mock_response1.json.return_value = scorecard_data
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.json.return_value = week_data
        mock_response2.raise_for_status = MagicMock()

        mock_async_client.get.side_effect = [mock_response1, mock_response2]

        # Get previous week's scores
        scorecards = await async_client.scorecard.list(week_offset=-1)

        assert len(scorecards) == 1
        assert scorecards[0].week_id == 23

    @pytest.mark.asyncio
    async def test_list_invalid_params(self, async_client: AsyncClient):
        """Test listing scorecards with both user_id and meeting_id raises error."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_client.scorecard.list(user_id=123, meeting_id=456)

    @pytest.mark.asyncio
    async def test_score(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test updating a score."""
        # Mock current week response
        week_data = {
            "Id": 2024,
            "ForWeekNumber": 24,
            "LocalDate": {"Date": "2024-06-10"},
            "ForWeek": "2024-06-16",
        }

        mock_week_response = MagicMock()
        mock_week_response.json.return_value = week_data
        mock_week_response.raise_for_status = MagicMock()

        mock_score_response = MagicMock()
        mock_score_response.raise_for_status = MagicMock()
        mock_score_response.is_success = True

        mock_async_client.get.return_value = mock_week_response
        mock_async_client.put.return_value = mock_score_response

        result = await async_client.scorecard.score(measurable_id=301, score=98.5)

        assert result is True
        mock_async_client.put.assert_called_once_with(
            "measurables/301/week/24", json={"value": 98.5}
        )

    @pytest.mark.asyncio
    async def test_score_with_week_offset(
        self, async_client: AsyncClient, mock_async_client: AsyncMock
    ):
        """Test updating a score with week offset."""
        # Mock current week response
        week_data = {
            "Id": 2024,
            "ForWeekNumber": 24,
            "LocalDate": {"Date": "2024-06-10"},
            "ForWeek": "2024-06-16",
        }

        mock_week_response = MagicMock()
        mock_week_response.json.return_value = week_data
        mock_week_response.raise_for_status = MagicMock()

        mock_score_response = MagicMock()
        mock_score_response.raise_for_status = MagicMock()
        mock_score_response.is_success = True

        mock_async_client.get.return_value = mock_week_response
        mock_async_client.put.return_value = mock_score_response

        # Update score for next week
        result = await async_client.scorecard.score(
            measurable_id=301, score=100, week_offset=1
        )

        assert result is True
        mock_async_client.put.assert_called_once_with(
            "measurables/301/week/25", json={"value": 100}
        )
