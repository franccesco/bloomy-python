"""Tests for the base operations module."""

from unittest.mock import Mock
import pytest
import httpx

from bloomy.utils.base_operations import BaseOperations


class TestBaseOperations:
    """Test cases for the BaseOperations class."""

    def test_initialization(self):
        """Test BaseOperations initialization."""
        mock_client = Mock(spec=httpx.Client)
        base_ops = BaseOperations(mock_client)
        
        assert base_ops._client == mock_client
        assert base_ops._user_id is None

    def test_user_id_lazy_loading(self):
        """Test user ID is loaded lazily."""
        mock_client = Mock(spec=httpx.Client)
        mock_response = Mock()
        mock_response.json.return_value = {"Id": 123}
        mock_client.get.return_value = mock_response
        
        base_ops = BaseOperations(mock_client)
        
        # User ID should be None initially
        assert base_ops._user_id is None
        
        # First access should trigger API call
        user_id = base_ops.user_id
        assert user_id == 123
        assert base_ops._user_id == 123
        
        # Second access should not trigger API call
        mock_client.get.reset_mock()
        user_id = base_ops.user_id
        assert user_id == 123
        mock_client.get.assert_not_called()

    def test_get_default_user_id(self):
        """Test _get_default_user_id method."""
        mock_client = Mock(spec=httpx.Client)
        mock_response = Mock()
        mock_response.json.return_value = {"Id": 456, "Name": "Test User"}
        mock_client.get.return_value = mock_response
        
        base_ops = BaseOperations(mock_client)
        user_id = base_ops._get_default_user_id()
        
        assert user_id == 456
        mock_client.get.assert_called_once_with("users/mine")
        mock_response.raise_for_status.assert_called_once()

    def test_get_default_user_id_error(self):
        """Test _get_default_user_id with API error."""
        mock_client = Mock(spec=httpx.Client)
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=Mock()
        )
        mock_client.get.return_value = mock_response
        
        base_ops = BaseOperations(mock_client)
        
        with pytest.raises(httpx.HTTPStatusError):
            base_ops._get_default_user_id()