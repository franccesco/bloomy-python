"""Tests for the Scorecard operations."""

from unittest.mock import Mock

import pytest

from bloomy.operations.scorecard import ScorecardOperations


class TestScorecardOperations:
    """Test cases for ScorecardOperations class."""

    def test_current_week(self, mock_http_client):
        """Test getting current week."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 2024025,
            "ForWeekNumber": 25,
            "LocalDate": {"Date": "2024-06-17"},
            "ForWeek": "2024-06-23"
        }
        mock_http_client.get.return_value = mock_response

        scorecard_ops = ScorecardOperations(mock_http_client)
        result = scorecard_ops.current_week()

        assert result["id"] == 2024025
        assert result["week_number"] == 25
        assert result["week_start"] == "2024-06-17"
        assert result["week_end"] == "2024-06-23"

        mock_http_client.get.assert_called_once_with("weeks/current")

    def test_list_user_scorecard(self, mock_http_client, sample_scorecard_data):
        """Test listing scorecard for a user."""
        mock_response = Mock()
        mock_response.json.return_value = sample_scorecard_data
        mock_http_client.get.return_value = mock_response

        scorecard_ops = ScorecardOperations(mock_http_client)
        scorecard_ops._user_id = 123

        result = scorecard_ops.list()

        assert len(result) == 1
        assert result[0]["id"] == 201
        assert result[0]["title"] == "Sales Revenue"
        assert result[0]["target"] == 100000
        assert result[0]["value"] == 95000

        mock_http_client.get.assert_called_once_with("scorecard/user/123")

    def test_list_meeting_scorecard(self, mock_http_client, sample_scorecard_data):
        """Test listing scorecard for a meeting."""
        mock_response = Mock()
        mock_response.json.return_value = sample_scorecard_data
        mock_http_client.get.return_value = mock_response

        scorecard_ops = ScorecardOperations(mock_http_client)
        result = scorecard_ops.list(meeting_id=456)

        assert len(result) == 1
        mock_http_client.get.assert_called_once_with("scorecard/meeting/456")

    def test_list_both_params_error(self, mock_http_client):
        """Test error when both user_id and meeting_id are provided."""
        scorecard_ops = ScorecardOperations(mock_http_client)

        with pytest.raises(ValueError) as exc_info:
            scorecard_ops.list(user_id=123, meeting_id=456)

        assert "Please provide either" in str(exc_info.value)

    def test_list_with_week_offset(self, mock_http_client):
        """Test listing scorecard with week offset."""
        # Mock scorecard response
        scorecard_response = Mock()
        scorecard_response.json.return_value = {
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
                    "DateEntered": "2024-06-20T10:00:00Z"
                },
                {
                    "Id": 202,
                    "MeasurableId": 302,
                    "AccountableUserId": 123,
                    "MeasurableName": "Customer Count",
                    "Target": 50,
                    "Measured": 48,
                    "Week": "2024-W24",
                    "ForWeek": 24,
                    "DateEntered": "2024-06-13T10:00:00Z"
                }
            ]
        }

        # Mock current week response
        week_response = Mock()
        week_response.json.return_value = {
            "Id": 2024025,
            "ForWeekNumber": 25,
            "LocalDate": {"Date": "2024-06-17"},
            "ForWeek": "2024-06-23"
        }

        mock_http_client.get.side_effect = [scorecard_response, week_response]

        scorecard_ops = ScorecardOperations(mock_http_client)
        scorecard_ops._user_id = 123

        result = scorecard_ops.list(week_offset=-1)

        # Should only return week 24 (25 - 1)
        assert len(result) == 1
        assert result[0]["week_id"] == 24

    def test_list_filter_empty_values(self, mock_http_client):
        """Test filtering empty values from scorecard."""
        mock_response = Mock()
        mock_response.json.return_value = {
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
                    "DateEntered": "2024-06-20T10:00:00Z"
                },
                {
                    "Id": 202,
                    "MeasurableId": 302,
                    "AccountableUserId": 123,
                    "MeasurableName": "Customer Count",
                    "Target": 50,
                    "Measured": None,  # Empty value
                    "Week": "2024-W25",
                    "ForWeek": 25,
                    "DateEntered": "2024-06-20T10:00:00Z"
                }
            ]
        }
        mock_http_client.get.return_value = mock_response

        scorecard_ops = ScorecardOperations(mock_http_client)
        scorecard_ops._user_id = 123

        # Without show_empty
        result = scorecard_ops.list()
        assert len(result) == 1
        assert result[0]["value"] == 95000

        # With show_empty
        result = scorecard_ops.list(show_empty=True)
        assert len(result) == 2

    def test_score(self, mock_http_client):
        """Test updating a score."""
        # Mock current week response
        week_response = Mock()
        week_response.json.return_value = {
            "Id": 2024025,
            "ForWeekNumber": 25,
            "LocalDate": {"Date": "2024-06-17"},
            "ForWeek": "2024-06-23"
        }

        # Mock score update response
        update_response = Mock()
        update_response.is_success = True

        mock_http_client.get.return_value = week_response
        mock_http_client.put.return_value = update_response

        scorecard_ops = ScorecardOperations(mock_http_client)
        result = scorecard_ops.score(measurable_id=301, score=97.5)

        assert result is True

        mock_http_client.put.assert_called_once_with(
            "measurables/301/week/25",
            json={"value": 97.5}
        )

    def test_score_with_week_offset(self, mock_http_client):
        """Test updating a score with week offset."""
        week_response = Mock()
        week_response.json.return_value = {
            "Id": 2024025,
            "ForWeekNumber": 25,
            "LocalDate": {"Date": "2024-06-17"},
            "ForWeek": "2024-06-23"
        }

        update_response = Mock()
        update_response.is_success = True

        mock_http_client.get.return_value = week_response
        mock_http_client.put.return_value = update_response

        scorecard_ops = ScorecardOperations(mock_http_client)
        result = scorecard_ops.score(measurable_id=301, score=97.5, week_offset=-1)

        assert result is True

        # Should update week 24 (25 - 1)
        mock_http_client.put.assert_called_once_with(
            "measurables/301/week/24",
            json={"value": 97.5}
        )
