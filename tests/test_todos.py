"""Tests for the Todos operations."""

from unittest.mock import Mock
import pytest

from bloomy.operations.todos import TodoOperations


class TestTodoOperations:
    """Test cases for TodoOperations class."""

    def test_list_user_todos(self, mock_http_client, sample_todo_data):
        """Test listing todos for a user."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_todo_data]
        mock_http_client.get.return_value = mock_response
        
        todo_ops = TodoOperations(mock_http_client)
        todo_ops._user_id = 123
        
        result = todo_ops.list()
        
        assert len(result) == 1
        assert result[0]["id"] == 789
        assert result[0]["title"] == "Complete project proposal"
        assert result[0]["status"] == "Incomplete"
        
        mock_http_client.get.assert_called_once_with("todo/user/123")

    def test_list_meeting_todos(self, mock_http_client, sample_todo_data):
        """Test listing todos for a meeting."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_todo_data]
        mock_http_client.get.return_value = mock_response
        
        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.list(meeting_id=456)
        
        assert len(result) == 1
        mock_http_client.get.assert_called_once_with("l10/456/todos")

    def test_list_both_params_error(self, mock_http_client):
        """Test error when both user_id and meeting_id are provided."""
        todo_ops = TodoOperations(mock_http_client)
        
        with pytest.raises(ValueError) as exc_info:
            todo_ops.list(user_id=123, meeting_id=456)
        
        assert "Please provide either" in str(exc_info.value)

    def test_create_todo(self, mock_http_client):
        """Test creating a todo."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 999,
            "Name": "New Todo",
            "DueDate": "2024-12-31",
            "DetailsUrl": "https://example.com/todo/999"
        }
        mock_http_client.post.return_value = mock_response
        
        todo_ops = TodoOperations(mock_http_client)
        todo_ops._user_id = 123
        
        result = todo_ops.create(
            title="New Todo",
            meeting_id=456,
            due_date="2024-12-31",
            notes="Important task"
        )
        
        assert result["id"] == 999
        assert result["title"] == "New Todo"
        
        mock_http_client.post.assert_called_once_with(
            "/api/v1/L10/456/todos",
            json={
                "title": "New Todo",
                "accountableUserId": 123,
                "notes": "Important task",
                "dueDate": "2024-12-31"
            }
        )

    def test_complete_todo(self, mock_http_client):
        """Test completing a todo."""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_response.is_success = True
        mock_http_client.post.return_value = mock_response
        
        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.complete(todo_id=789)
        
        assert result is True
        mock_http_client.post.assert_called_once_with("/api/v1/todo/789/complete?status=true")

    def test_update_todo(self, mock_http_client):
        """Test updating a todo."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 789,
            "Name": "Updated Todo",
            "DueDate": "2024-11-01"
        }
        mock_response.status_code = 200
        mock_http_client.put.return_value = mock_response
        
        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.update(
            todo_id=789,
            title="Updated Todo",
            due_date="2024-11-01"
        )
        
        assert result["id"] == 789
        assert result["title"] == "Updated Todo"
        assert result["due_date"] == "2024-11-01"
        
        mock_http_client.put.assert_called_once_with(
            "/api/v1/todo/789",
            json={"title": "Updated Todo", "dueDate": "2024-11-01"}
        )

    def test_update_todo_no_fields(self, mock_http_client):
        """Test updating todo with no fields raises error."""
        todo_ops = TodoOperations(mock_http_client)
        
        with pytest.raises(ValueError) as exc_info:
            todo_ops.update(todo_id=789)
        
        assert "At least one field" in str(exc_info.value)

    def test_details(self, mock_http_client):
        """Test getting todo details."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 789,
            "Name": "Test Todo",
            "DetailsUrl": "https://example.com/todo/789",
            "DueDate": "2024-12-31",
            "CreateTime": "2024-01-01T10:00:00Z",
            "CompleteTime": None,
            "Complete": False
        }
        mock_response.is_success = True
        mock_http_client.get.return_value = mock_response
        
        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.details(todo_id=789)
        
        assert result["id"] == 789
        assert result["title"] == "Test Todo"
        assert result["status"] == "Incomplete"
        
        mock_http_client.get.assert_called_once_with("/api/v1/todo/789")