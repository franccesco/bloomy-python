"""Tests for the Meetings operations."""

from typing import Any
from unittest.mock import Mock

import pytest

from bloomy.operations.meetings import MeetingOperations


class TestMeetingOperations:
    """Test cases for MeetingOperations class."""

    def test_list_meetings(self, mock_http_client: Mock, mock_user_id: Mock) -> None:
        """Test listing meetings."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 456,
                "Type": "NameId",
                "Key": "NameId_456",
                "Name": "Weekly Team Meeting",
            },
            {
                "Id": 789,
                "Type": "NameId",
                "Key": "NameId_789",
                "Name": "Monthly Review",
            },
        ]
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.list()

        assert len(result) == 2
        assert result[0].id == 456
        assert result[0].name == "Weekly Team Meeting"
        assert result[1].id == 789

        mock_http_client.get.assert_called_once_with("L10/123/list")

    def test_attendees(self, mock_http_client: Mock) -> None:
        """Test getting meeting attendees."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"Id": 123, "Name": "John Doe", "ImageUrl": "https://example.com/john.jpg"},
            {
                "Id": 456,
                "Name": "Jane Smith",
                "ImageUrl": "https://example.com/jane.jpg",
            },
        ]
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.attendees(meeting_id=789)

        assert len(result) == 2
        assert result[0].user_id == 123
        assert result[0].name == "John Doe"

        mock_http_client.get.assert_called_once_with("L10/789/attendees")

    def test_issues(self, mock_http_client: Mock) -> None:
        """Test getting meeting issues."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 101,
                "Name": "Server issue",
                "DetailsUrl": "https://example.com/issue/101",
                "CreateTime": "2024-06-01T10:00:00Z",
                "CloseTime": None,
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Origin": "Infrastructure Meeting",
            }
        ]
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.issues(meeting_id=789)

        assert len(result) == 1
        assert result[0].id == 101
        assert result[0].name == "Server issue"
        assert result[0].owner_id == 123
        assert result[0].meeting_id == 789

        mock_http_client.get.assert_called_once_with(
            "L10/789/issues", params={"include_resolved": False}
        )

    def test_todos(
        self, mock_http_client: Mock, sample_todo_data: dict[str, Any]
    ) -> None:
        """Test getting meeting todos."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_todo_data]
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.todos(meeting_id=456, include_closed=True)

        assert len(result) == 1
        assert result[0].id == 789
        assert result[0].name == "Complete project proposal"
        assert result[0].complete_date is None

        mock_http_client.get.assert_called_once_with(
            "L10/456/todos", params={"INCLUDE_CLOSED": True}
        )

    def test_metrics(self, mock_http_client: Mock) -> None:
        """Test getting meeting metrics."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 201,
                "Name": "Sales Revenue",
                "Target": 100000,
                "Direction": ">=",
                "Modifiers": "currency",
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Admin": {"Id": 456, "Name": "Jane Smith"},
            },
            {
                "Id": None,  # Should be skipped
                "Name": "Invalid Metric",
            },
        ]
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.metrics(meeting_id=789)

        assert len(result) == 1  # Only valid metric
        assert result[0].id == 201
        assert result[0].title == "Sales Revenue"
        assert result[0].target == 100000.0

        mock_http_client.get.assert_called_once_with("L10/789/measurables")

    def test_metrics_not_list(self, mock_http_client: Mock) -> None:
        """Test metrics when response is not a list."""
        mock_response = Mock()
        mock_response.json.return_value = None
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.metrics(meeting_id=789)

        assert result == []

    def test_details(self, mock_http_client: Mock, mock_user_id: Mock) -> None:
        """Test getting meeting details."""
        # Mock list response
        list_response = Mock()
        list_response.json.return_value = [
            {
                "Id": 789,
                "Type": "NameId",
                "Key": "NameId_789",
                "Name": "Team Meeting",
            }
        ]

        # Mock other responses
        attendees_response = Mock()
        attendees_response.json.return_value = []

        issues_response = Mock()
        issues_response.json.return_value = []

        todos_response = Mock()
        todos_response.json.return_value = []

        metrics_response = Mock()
        metrics_response.json.return_value = []

        mock_http_client.get.side_effect = [
            list_response,
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
        ]

        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.details(meeting_id=789)

        assert result.id == 789
        assert result.name == "Team Meeting"
        assert result.attendees is not None
        assert result.issues is not None
        assert result.todos is not None
        assert result.metrics is not None

    def test_details_meeting_not_found(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test getting details for non-existent meeting."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_http_client.get.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)

        from bloomy.exceptions import APIError
        with pytest.raises(APIError) as exc_info:
            meeting_ops.details(meeting_id=999)

        assert "Meeting with ID 999 not found" in str(exc_info.value)

    def test_create_meeting(self, mock_http_client: Mock) -> None:
        """Test creating a meeting."""
        mock_response = Mock()
        mock_response.json.return_value = {"meetingId": 999}
        mock_http_client.post.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.create(
            title="New Meeting", add_self=True, attendees=[123, 456]
        )

        assert result["meeting_id"] == 999
        assert result["title"] == "New Meeting"
        assert result["attendees"] == [123, 456]

        # Check create call
        mock_http_client.post.assert_any_call(
            "L10/create", json={"title": "New Meeting", "addSelf": True}
        )

        # Check attendee calls
        assert mock_http_client.post.call_count == 3  # 1 create + 2 attendees

    def test_delete_meeting(self, mock_http_client: Mock) -> None:
        """Test deleting a meeting."""
        mock_response = Mock()
        mock_http_client.delete.return_value = mock_response

        meeting_ops = MeetingOperations(mock_http_client)
        result = meeting_ops.delete(meeting_id=789)

        assert result is True
        mock_http_client.delete.assert_called_once_with("L10/789")
