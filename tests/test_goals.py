"""Tests for the Goals operations."""

from unittest.mock import Mock
import pytest

from bloomy.operations.goals import GoalOperations


class TestGoalOperations:
    """Test cases for GoalOperations class."""

    def test_list_goals(self, mock_http_client, sample_goal_data):
        """Test listing goals."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_goal_data]
        mock_http_client.get.return_value = mock_response
        
        goal_ops = GoalOperations(mock_http_client)
        goal_ops._user_id = 123
        
        result = goal_ops.list()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == 101
        assert result[0]["title"] == "Increase sales by 20%"
        assert result[0]["status"] == "Incomplete"
        
        mock_http_client.get.assert_called_once_with(
            "rocks/user/123", 
            params={"include_origin": True}
        )

    def test_list_goals_with_archived(self, mock_http_client, sample_goal_data):
        """Test listing goals with archived."""
        # Mock active goals response
        active_response = Mock()
        active_response.json.return_value = [sample_goal_data]
        
        # Mock archived goals response  
        archived_response = Mock()
        archived_response.json.return_value = [
            {
                "Id": 102,
                "Name": "Old Goal",
                "CreateTime": "2023-01-01T10:00:00Z",
                "DueDate": "2023-12-31",
                "Complete": True
            }
        ]
        
        mock_http_client.get.side_effect = [active_response, archived_response]
        
        goal_ops = GoalOperations(mock_http_client)
        goal_ops._user_id = 123
        
        result = goal_ops.list(archived=True)
        
        assert isinstance(result, dict)
        assert "active" in result
        assert "archived" in result
        assert len(result["active"]) == 1
        assert len(result["archived"]) == 1

    def test_create_goal(self, mock_http_client):
        """Test creating a goal."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 999,
            "Name": "New Goal",
            "Owner": {"Id": 456, "Name": "Jane Smith"},
            "Origins": [{"Id": 789, "Name": "Planning Meeting"}],
            "CreateTime": "2024-06-01T10:00:00Z",
            "Completion": 0
        }
        mock_http_client.post.return_value = mock_response
        
        goal_ops = GoalOperations(mock_http_client)
        goal_ops._user_id = 123
        
        result = goal_ops.create(
            title="New Goal",
            meeting_id=789,
            user_id=456
        )
        
        assert result["id"] == 999
        assert result["title"] == "New Goal"
        assert result["user_id"] == 456
        assert result["meeting_id"] == 789
        assert result["meeting_title"] == "Planning Meeting"
        
        mock_http_client.post.assert_called_once_with(
            "L10/789/rocks",
            json={
                "title": "New Goal",
                "accountableUserId": 456
            }
        )

    def test_delete_goal(self, mock_http_client):
        """Test deleting a goal."""
        mock_response = Mock()
        mock_http_client.delete.return_value = mock_response
        
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.delete(goal_id=101)
        
        assert result is True
        mock_http_client.delete.assert_called_once_with("rocks/101")

    def test_update_goal(self, mock_http_client):
        """Test updating a goal."""
        mock_response = Mock()
        mock_http_client.put.return_value = mock_response
        
        goal_ops = GoalOperations(mock_http_client)
        goal_ops._user_id = 123
        
        result = goal_ops.update(
            goal_id=101,
            title="Updated Goal",
            status="complete"
        )
        
        assert result is True
        mock_http_client.put.assert_called_once_with(
            "rocks/101",
            json={
                "accountableUserId": 123,
                "title": "Updated Goal",
                "completion": "Complete"
            }
        )

    def test_update_goal_invalid_status(self, mock_http_client):
        """Test updating goal with invalid status."""
        goal_ops = GoalOperations(mock_http_client)
        goal_ops._user_id = 123
        
        with pytest.raises(ValueError) as exc_info:
            goal_ops.update(goal_id=101, status="invalid")
        
        assert "Invalid status value" in str(exc_info.value)

    def test_archive_goal(self, mock_http_client):
        """Test archiving a goal."""
        mock_response = Mock()
        mock_http_client.put.return_value = mock_response
        
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.archive(goal_id=101)
        
        assert result is True
        mock_http_client.put.assert_called_once_with("rocks/101/archive")

    def test_restore_goal(self, mock_http_client):
        """Test restoring a goal."""
        mock_response = Mock()
        mock_http_client.put.return_value = mock_response
        
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.restore(goal_id=101)
        
        assert result is True
        mock_http_client.put.assert_called_once_with("rocks/101/restore")