"""Tests for model validators."""

from datetime import datetime

from bloomy.models import Goal, Issue, Todo


class TestModelValidators:
    """Test cases for model field validators."""

    def test_todo_empty_string_dates(self) -> None:
        """Test Todo model with empty string dates."""
        todo_data = {
            "Id": 1,
            "Name": "Test Todo",
            "DetailsUrl": "https://example.com/todo/1",
            "DueDate": "",  # Empty string should become None
            "CompleteTime": "",  # Empty string should become None
            "CreateTime": "2024-01-01T10:00:00Z",
            "OriginId": 123,
            "Origin": "Meeting",
            "Complete": False,
        }

        todo = Todo(**todo_data)
        assert todo.due_date is None
        assert todo.complete_date is None
        assert isinstance(todo.create_date, datetime)

    def test_issue_empty_string_dates(self) -> None:
        """Test Issue model with empty string dates."""
        issue_data = {
            "Id": 1,
            "Name": "Test Issue",
            "DetailsUrl": "https://example.com/issue/1",
            "CreateDate": "2024-01-01T10:00:00Z",
            "MeetingId": 123,
            "MeetingName": "Weekly Meeting",
            "OwnerName": "John Doe",
            "OwnerId": 456,
            "OwnerImageUrl": "https://example.com/avatar.jpg",
            "ClosedDate": "",  # Empty string should become None
            "CompletionDate": "",  # Empty string should become None
        }

        issue = Issue(**issue_data)
        assert issue.closed_date is None
        assert issue.completion_date is None
        assert isinstance(issue.created_date, datetime)

    def test_goal_empty_string_complete_date(self) -> None:
        """Test Goal model with empty string complete date."""
        goal_data = {
            "Id": 1,
            "Name": "Q1 Revenue Goal",
            "DueDate": "2024-03-31T23:59:59Z",
            "CompleteDate": "",  # Empty string should become None
            "CreateDate": "2024-01-01T10:00:00Z",
            "IsArchived": False,
            "PercentComplete": 50.0,
            "AccountableUserId": 123,
            "AccountableUserName": "Jane Smith",
        }

        goal = Goal(**goal_data)
        assert goal.complete_date is None
        assert isinstance(goal.due_date, datetime)
        assert isinstance(goal.create_date, datetime)
