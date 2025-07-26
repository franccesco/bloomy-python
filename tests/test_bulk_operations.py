"""Tests for bulk creation operations."""

from typing import Any
from unittest.mock import Mock

from httpx import HTTPStatusError, Request, Response

from bloomy.models import BulkCreateResult
from bloomy.operations.goals import GoalOperations
from bloomy.operations.issues import IssueOperations
from bloomy.operations.meetings import MeetingOperations
from bloomy.operations.todos import TodoOperations


class TestBulkIssueOperations:
    """Test cases for bulk issue operations."""

    def test_create_many_all_success(
        self,
        mock_http_client: Mock,
        sample_issue_data: dict[str, Any],
        mock_user_id: Mock,
    ) -> None:
        """Test creating multiple issues when all succeed."""
        # Set up sequential responses for each create call
        responses = []
        for i in range(3):
            mock_response = Mock()
            mock_response.json.return_value = {
                **sample_issue_data,
                "Id": 401 + i,
                "Name": f"Issue {i + 1}",
            }
            mock_response.raise_for_status = Mock()
            responses.append(mock_response)

        mock_http_client.post.side_effect = responses

        issue_ops = IssueOperations(mock_http_client)

        issues_data = [
            {"meeting_id": 456, "title": "Issue 1", "notes": "Details 1"},
            {"meeting_id": 456, "title": "Issue 2"},
            {"meeting_id": 456, "title": "Issue 3", "user_id": 999},
        ]

        result = issue_ops.create_many(issues_data)

        assert isinstance(result, BulkCreateResult)
        assert len(result.successful) == 3
        assert len(result.failed) == 0

        # Check each successful creation
        assert result.successful[0].id == 401
        assert result.successful[0].title == "Issue 1"
        assert result.successful[1].id == 402
        assert result.successful[2].id == 403

        # Verify API calls
        assert mock_http_client.post.call_count == 3

    def test_create_many_partial_failure(
        self,
        mock_http_client: Mock,
        sample_issue_data: dict[str, Any],
        mock_user_id: Mock,
    ) -> None:
        """Test creating multiple issues with some failures."""
        # First succeeds
        success_response = Mock()
        success_response.json.return_value = sample_issue_data
        success_response.raise_for_status = Mock()

        # Second fails
        fail_response = Mock()
        fail_response.raise_for_status.side_effect = HTTPStatusError(
            "Server error",
            request=Mock(spec=Request),
            response=Mock(spec=Response, status_code=500),
        )

        # Third succeeds
        success_response2 = Mock()
        success_response2.json.return_value = {**sample_issue_data, "Id": 403}
        success_response2.raise_for_status = Mock()

        mock_http_client.post.side_effect = [
            success_response,
            fail_response,
            success_response2,
        ]

        issue_ops = IssueOperations(mock_http_client)

        issues_data = [
            {"meeting_id": 456, "title": "Issue 1"},
            {"meeting_id": 456, "title": "Issue 2"},
            {"meeting_id": 456, "title": "Issue 3"},
        ]

        result = issue_ops.create_many(issues_data)

        assert len(result.successful) == 2
        assert len(result.failed) == 1

        # Check failure details
        assert result.failed[0].index == 1
        assert result.failed[0].input_data == {"meeting_id": 456, "title": "Issue 2"}
        assert "Server error" in result.failed[0].error

    def test_create_many_validation_error(
        self,
        mock_http_client: Mock,
        mock_user_id: Mock,
        sample_issue_data: dict[str, Any],
    ) -> None:
        """Test creating issues with validation errors."""
        # Set up response for the valid issue
        mock_response = Mock()
        mock_response.json.return_value = sample_issue_data
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        issue_ops = IssueOperations(mock_http_client)

        issues_data = [
            {"meeting_id": 456, "title": "Valid Issue"},
            {"title": "Missing meeting_id"},  # Missing required field
            {"meeting_id": 456},  # Missing title
        ]

        result = issue_ops.create_many(issues_data)

        # Should have 1 success and 2 validation failures
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.failed[0].index == 1
        assert "meeting_id" in result.failed[0].error
        assert result.failed[1].index == 2
        assert "title" in result.failed[1].error

        # Only the valid one should be attempted
        assert mock_http_client.post.call_count == 1


class TestBulkTodoOperations:
    """Test cases for bulk todo operations."""

    def test_create_many_todos_success(
        self,
        mock_http_client: Mock,
        sample_todo_data: dict[str, Any],
        mock_user_id: Mock,
    ) -> None:
        """Test creating multiple todos successfully."""
        responses = []
        for i in range(2):
            mock_response = Mock()
            mock_response.json.return_value = {
                "Id": 789 + i,
                "Name": f"Todo {i + 1}",
                "DueDate": "2024-12-31",
                "DetailsUrl": None,
            }
            mock_response.raise_for_status = Mock()
            responses.append(mock_response)

        mock_http_client.post.side_effect = responses

        todo_ops = TodoOperations(mock_http_client)

        todos_data = [
            {"title": "Todo 1", "meeting_id": 456, "due_date": "2024-12-31"},
            {"title": "Todo 2", "meeting_id": 456, "notes": "Important task"},
        ]

        result = todo_ops.create_many(todos_data)

        assert len(result.successful) == 2
        assert len(result.failed) == 0
        assert result.successful[0].id == 789
        assert result.successful[0].name == "Todo 1"
        assert result.successful[1].id == 790

    def test_create_many_todos_validation(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test todo validation in bulk creation."""
        # Set up response for the valid todo
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 789,
            "Name": "Valid Todo",
            "DueDate": None,
            "DetailsUrl": None,
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        todo_ops = TodoOperations(mock_http_client)

        todos_data = [
            {"meeting_id": 456},  # Missing title
            {"title": "Valid Todo", "meeting_id": 456},
            {"title": "Missing meeting"},  # Missing meeting_id
        ]

        result = todo_ops.create_many(todos_data)

        # Should have 1 success and 2 validation failures
        assert len(result.successful) == 1
        assert len(result.failed) == 2
        assert result.failed[0].index == 0
        assert "title" in result.failed[0].error
        assert result.failed[1].index == 2
        assert "meeting_id" in result.failed[1].error

        # Only valid one should be attempted
        assert mock_http_client.post.call_count == 1


class TestBulkGoalOperations:
    """Test cases for bulk goal operations."""

    def test_create_many_goals_success(
        self,
        mock_http_client: Mock,
        sample_goal_data: dict[str, Any],
        mock_user_id: Mock,
    ) -> None:
        """Test creating multiple goals successfully."""
        mock_response = Mock()
        mock_response.json.return_value = {
            **sample_goal_data,
            "Completion": 0,
        }
        mock_response.raise_for_status = Mock()
        mock_http_client.post.return_value = mock_response

        goal_ops = GoalOperations(mock_http_client)

        goals_data = [
            {"title": "Goal 1", "meeting_id": 456},
            {"title": "Goal 2", "meeting_id": 456, "user_id": 999},
        ]

        result = goal_ops.create_many(goals_data)

        assert len(result.successful) == 2
        assert len(result.failed) == 0
        assert result.successful[0].title == "Goal 1"
        assert result.successful[1].title == "Goal 2"

    def test_create_many_goals_empty_list(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test creating goals with empty list."""
        goal_ops = GoalOperations(mock_http_client)

        result = goal_ops.create_many([])

        assert len(result.successful) == 0
        assert len(result.failed) == 0
        assert mock_http_client.post.call_count == 0


class TestBulkMeetingOperations:
    """Test cases for bulk meeting operations."""

    def test_create_many_meetings_success(self, mock_http_client: Mock) -> None:
        """Test creating multiple meetings successfully."""
        # Create responses for meeting creation and attendee addition
        create_responses = []
        for i in range(2):
            mock_response = Mock()
            mock_response.json.return_value = {
                "meetingId": 456 + i,  # Note: API returns meetingId, not meeting_id
            }
            mock_response.raise_for_status = Mock()
            create_responses.append(mock_response)

        # Add mock responses for attendee additions
        # (3 for first meeting, none for second)
        attendee_responses = []
        for _ in range(3):
            attendee_response = Mock()
            attendee_response.raise_for_status = Mock()
            attendee_responses.append(attendee_response)

        # Create a list to track all responses in order
        all_responses = []
        # First meeting create
        all_responses.append(create_responses[0])
        # First meeting attendee additions (3)
        all_responses.extend(attendee_responses[:3])
        # Second meeting create
        all_responses.append(create_responses[1])
        # No attendee additions for second meeting

        mock_http_client.post.side_effect = all_responses

        meeting_ops = MeetingOperations(mock_http_client)

        meetings_data = [
            {"title": "Meeting 1", "attendees": [1, 2, 3]},
            {"title": "Meeting 2", "add_self": False},
        ]

        result = meeting_ops.create_many(meetings_data)

        assert len(result.successful) == 2
        assert len(result.failed) == 0
        assert result.successful[0]["meeting_id"] == 456
        assert result.successful[0]["title"] == "Meeting 1"
        assert result.successful[0]["attendees"] == [1, 2, 3]
        assert result.successful[1]["meeting_id"] == 457
        assert result.successful[1]["title"] == "Meeting 2"
        assert result.successful[1]["attendees"] == []

    def test_create_many_meetings_with_exception(self, mock_http_client: Mock) -> None:
        """Test meeting creation with unexpected exception."""
        mock_http_client.post.side_effect = Exception("Network error")

        meeting_ops = MeetingOperations(mock_http_client)

        meetings_data = [{"title": "Meeting 1"}]

        result = meeting_ops.create_many(meetings_data)

        assert len(result.successful) == 0
        assert len(result.failed) == 1
        assert result.failed[0].index == 0
        assert "Network error" in result.failed[0].error

    def test_get_many_all_success(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test retrieving multiple meetings when all succeed."""
        # Mock list response for finding meetings
        list_response = Mock()
        list_response.json.return_value = [
            {"Id": 456, "Type": "NameId", "Key": "NameId_456", "Name": "Meeting 1"},
            {"Id": 457, "Type": "NameId", "Key": "NameId_457", "Name": "Meeting 2"},
            {"Id": 458, "Type": "NameId", "Key": "NameId_458", "Name": "Meeting 3"},
        ]

        # Mock responses for each meeting's details
        attendees_response = Mock()
        attendees_response.json.return_value = [
            {"Id": 123, "Name": "John Doe", "ImageUrl": "https://example.com/john.jpg"}
        ]

        issues_response = Mock()
        issues_response.json.return_value = []

        todos_response = Mock()
        todos_response.json.return_value = []

        metrics_response = Mock()
        metrics_response.json.return_value = []

        # Set up the side effect for all calls
        # Pattern: list, attendees, issues, todos, metrics (repeated for each meeting)
        mock_http_client.get.side_effect = [
            list_response,  # For finding meeting 456
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
            list_response,  # For finding meeting 457
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
            list_response,  # For finding meeting 458
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
        ]

        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.get_many([456, 457, 458])

        assert isinstance(result, BulkCreateResult)
        assert len(result.successful) == 3
        assert len(result.failed) == 0

        # Check successful meetings
        assert result.successful[0].id == 456
        assert result.successful[0].name == "Meeting 1"
        assert result.successful[1].id == 457
        assert result.successful[1].name == "Meeting 2"
        assert result.successful[2].id == 458
        assert result.successful[2].name == "Meeting 3"

        # Verify all API calls were made (5 calls per meeting)
        assert mock_http_client.get.call_count == 15

    def test_get_many_partial_failure(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test retrieving multiple meetings with some failures."""
        # Mock list response for finding meetings
        list_response = Mock()
        list_response.json.return_value = [
            {"Id": 456, "Type": "NameId", "Key": "NameId_456", "Name": "Meeting 1"},
        ]

        empty_list_response = Mock()
        empty_list_response.json.return_value = []  # Meeting not found

        # Mock responses for meeting details
        attendees_response = Mock()
        attendees_response.json.return_value = []

        issues_response = Mock()
        issues_response.json.return_value = []

        todos_response = Mock()
        todos_response.json.return_value = []

        metrics_response = Mock()
        metrics_response.json.return_value = []

        # Set up the side effect
        mock_http_client.get.side_effect = [
            list_response,  # First meeting found
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
            empty_list_response,  # Second meeting not found
            list_response,  # Third meeting found
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
        ]

        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.get_many([456, 999, 456])  # 999 doesn't exist

        assert len(result.successful) == 2
        assert len(result.failed) == 1

        # Check failure details
        assert result.failed[0].index == 1
        assert result.failed[0].input_data == {"meeting_id": 999}
        assert "Meeting with ID 999 not found" in result.failed[0].error

    def test_get_many_empty_list(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test retrieving meetings with empty list."""
        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.get_many([])

        assert len(result.successful) == 0
        assert len(result.failed) == 0
        assert mock_http_client.get.call_count == 0

    def test_get_many_network_error(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test retrieving meetings with network errors."""
        # First meeting succeeds
        list_response = Mock()
        list_response.json.return_value = [
            {"Id": 456, "Type": "NameId", "Key": "NameId_456", "Name": "Meeting 1"},
        ]

        attendees_response = Mock()
        attendees_response.json.return_value = []

        issues_response = Mock()
        issues_response.json.return_value = []

        todos_response = Mock()
        todos_response.json.return_value = []

        metrics_response = Mock()
        metrics_response.json.return_value = []

        # Set up side effect with network error on second meeting
        mock_http_client.get.side_effect = [
            list_response,  # First meeting list
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
            Exception("Network error"),  # Network error on second meeting list
        ]

        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.get_many([456, 457])

        assert len(result.successful) == 1
        assert len(result.failed) == 1
        assert result.successful[0].id == 456
        assert result.failed[0].index == 1
        assert "Network error" in result.failed[0].error

    def test_get_many_duplicate_ids(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test retrieving meetings with duplicate IDs."""
        # Mock list response
        list_response = Mock()
        list_response.json.return_value = [
            {"Id": 456, "Type": "NameId", "Key": "NameId_456", "Name": "Meeting 1"},
        ]

        # Mock responses for meeting details
        attendees_response = Mock()
        attendees_response.json.return_value = []

        issues_response = Mock()
        issues_response.json.return_value = []

        todos_response = Mock()
        todos_response.json.return_value = []

        metrics_response = Mock()
        metrics_response.json.return_value = []

        # Set up the side effect (need responses for two calls to same meeting)
        mock_http_client.get.side_effect = [
            list_response,  # First call for meeting 456
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
            list_response,  # Second call for meeting 456
            attendees_response,
            issues_response,
            todos_response,
            metrics_response,
        ]

        meeting_ops = MeetingOperations(mock_http_client)

        result = meeting_ops.get_many([456, 456])

        assert len(result.successful) == 2
        assert len(result.failed) == 0
        assert result.successful[0].id == 456
        assert result.successful[1].id == 456

        # Should make 10 calls (5 per meeting retrieval)
        assert mock_http_client.get.call_count == 10
