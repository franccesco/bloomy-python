"""Tests for the Issues operations."""

from typing import Any
from unittest.mock import Mock

import pytest

from bloomy.operations.issues import IssueOperations


class TestIssueOperations:
    """Test cases for IssueOperations class."""

    def test_details(
        self, mock_http_client: Mock, sample_issue_data: dict[str, Any]
    ) -> None:
        """Test getting issue details."""
        mock_response = Mock()
        mock_response.json.return_value = sample_issue_data
        mock_http_client.get.return_value = mock_response

        issue_ops = IssueOperations(mock_http_client)
        result = issue_ops.details(issue_id=401)

        assert result.id == 401
        assert result.title == "Server performance issue"
        assert result.notes_url == "https://example.com/issue/401"
        assert result.user_id == 123
        assert result.meeting_id == 456

        mock_http_client.get.assert_called_once_with("issues/401")

    def test_list_user_issues(self, mock_http_client: Mock, mock_user_id: Mock) -> None:
        """Test listing issues for a user."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 401,
                "Name": "Server issue",
                "CreateTime": "2024-06-01T10:00:00Z",
                "Origin": "Infrastructure Meeting",
                "OriginId": 456,
                "DetailsUrl": "https://example.com/issue/401",
            }
        ]
        mock_http_client.get.return_value = mock_response

        issue_ops = IssueOperations(mock_http_client)

        result = issue_ops.list()

        assert len(result) == 1
        assert result[0].id == 401
        assert result[0].title == "Server issue"
        assert result[0].created_at == "2024-06-01T10:00:00Z"
        assert result[0].meeting_title == "Infrastructure Meeting"

        mock_http_client.get.assert_called_once_with("issues/users/123")

    def test_list_meeting_issues(self, mock_http_client: Mock) -> None:
        """Test listing issues for a meeting."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 401,
                "Name": "Server issue",
                "CreateTime": "2024-06-01T10:00:00Z",
                "Origin": "Infrastructure Meeting",
                "OriginId": 456,
                "DetailsUrl": "https://example.com/issue/401",
            }
        ]
        mock_http_client.get.return_value = mock_response

        issue_ops = IssueOperations(mock_http_client)
        result = issue_ops.list(meeting_id=456)

        assert len(result) == 1
        mock_http_client.get.assert_called_once_with("l10/456/issues")

    def test_list_both_params_error(self, mock_http_client: Mock) -> None:
        """Test error when both user_id and meeting_id are provided."""
        issue_ops = IssueOperations(mock_http_client)

        with pytest.raises(ValueError) as exc_info:
            issue_ops.list(user_id=123, meeting_id=456)

        assert "Please provide either" in str(exc_info.value)

    def test_complete(
        self, mock_http_client: Mock, sample_issue_data: dict[str, Any]
    ) -> None:
        """Test completing an issue."""
        # Mock the complete POST response
        post_response = Mock()
        mock_http_client.post.return_value = post_response

        # Mock the details GET response
        get_response = Mock()
        get_response.json.return_value = sample_issue_data
        mock_http_client.get.return_value = get_response

        issue_ops = IssueOperations(mock_http_client)
        result = issue_ops.complete(issue_id=401)

        assert isinstance(result, type(issue_ops.details(401)))
        assert result.id == 401
        mock_http_client.post.assert_called_once_with(
            "issues/401/complete", json={"complete": True}
        )

    def test_create(self, mock_http_client: Mock, mock_user_id: Mock) -> None:
        """Test creating an issue."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 999,
            "OriginId": 456,
            "Origin": "Planning Meeting",
            "Name": "New Issue",
            "Owner": {"Id": 789},
            "DetailsUrl": "https://example.com/issue/999",
        }
        mock_http_client.post.return_value = mock_response

        issue_ops = IssueOperations(mock_http_client)

        result = issue_ops.create(
            meeting_id=456, title="New Issue", user_id=789, notes="Issue description"
        )

        assert result.id == 999
        assert result.title == "New Issue"
        assert result.user_id == 789
        assert result.meeting_id == 456

        mock_http_client.post.assert_called_once_with(
            "issues/create",
            json={
                "title": "New Issue",
                "ownerid": 789,
                "meetingid": 456,
                "notes": "Issue description",
            },
        )

    def test_create_default_user(
        self, mock_http_client: Mock, mock_user_id: Mock
    ) -> None:
        """Test creating an issue with default user."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 999,
            "OriginId": 456,
            "Origin": "Planning Meeting",
            "Name": "New Issue",
            "Owner": {"Id": 123},
            "DetailsUrl": "https://example.com/issue/999",
        }
        mock_http_client.post.return_value = mock_response

        issue_ops = IssueOperations(mock_http_client)

        result = issue_ops.create(meeting_id=456, title="New Issue")

        assert result.user_id == 123

        mock_http_client.post.assert_called_once_with(
            "issues/create",
            json={"title": "New Issue", "ownerid": 123, "meetingid": 456},
        )

    def test_update(
        self, mock_http_client: Mock, sample_issue_data: dict[str, Any]
    ) -> None:
        """Test updating an issue."""
        # Mock the update PUT response
        put_response = Mock()
        mock_http_client.put.return_value = put_response

        # Mock the details GET response
        get_response = Mock()
        updated_data = sample_issue_data.copy()
        updated_data["Name"] = "Updated Title"
        get_response.json.return_value = updated_data
        mock_http_client.get.return_value = get_response

        issue_ops = IssueOperations(mock_http_client)
        result = issue_ops.update(issue_id=401, title="Updated Title")

        assert result.id == 401
        assert result.title == "Updated Title"
        mock_http_client.put.assert_called_once_with(
            "issues/401", json={"title": "Updated Title"}
        )

    def test_update_with_notes(
        self, mock_http_client: Mock, sample_issue_data: dict[str, Any]
    ) -> None:
        """Test updating an issue with notes."""
        put_response = Mock()
        mock_http_client.put.return_value = put_response

        get_response = Mock()
        get_response.json.return_value = sample_issue_data
        mock_http_client.get.return_value = get_response

        issue_ops = IssueOperations(mock_http_client)
        result = issue_ops.update(issue_id=401, notes="Updated notes")

        assert result.id == 401
        mock_http_client.put.assert_called_once_with(
            "issues/401", json={"notes": "Updated notes"}
        )

    def test_update_both_fields(
        self, mock_http_client: Mock, sample_issue_data: dict[str, Any]
    ) -> None:
        """Test updating an issue with both title and notes."""
        put_response = Mock()
        mock_http_client.put.return_value = put_response

        get_response = Mock()
        get_response.json.return_value = sample_issue_data
        mock_http_client.get.return_value = get_response

        issue_ops = IssueOperations(mock_http_client)
        result = issue_ops.update(
            issue_id=401, title="Updated Title", notes="Updated notes"
        )

        assert result.id == 401
        mock_http_client.put.assert_called_once_with(
            "issues/401", json={"title": "Updated Title", "notes": "Updated notes"}
        )

    def test_update_no_fields(self, mock_http_client: Mock) -> None:
        """Test updating an issue with no fields raises ValueError."""
        issue_ops = IssueOperations(mock_http_client)

        with pytest.raises(ValueError) as exc_info:
            issue_ops.update(issue_id=401)

        assert "At least one field" in str(exc_info.value)
