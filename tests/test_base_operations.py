"""Tests for the base operations module."""

from unittest.mock import Mock

import httpx
import pytest

from bloomy.utils.base_operations import BaseOperations


class TestBaseOperations:
    """Test cases for the BaseOperations class."""

    def test_initialization(self):
        """Test BaseOperations initialization."""
        mock_client = Mock(spec=httpx.Client)
        base_ops = BaseOperations(mock_client)

        # Test that the object is properly initialized
        # We can't directly check private attributes in strict mode
        assert isinstance(base_ops, BaseOperations)

    def test_user_id_lazy_loading(self):
        """Test user ID is loaded lazily."""
        mock_client = Mock(spec=httpx.Client)
        mock_response = Mock()
        mock_response.json.return_value = {"Id": 123}
        mock_client.get.return_value = mock_response

        base_ops = BaseOperations(mock_client)

        # First access should trigger API call
        user_id = base_ops.user_id
        assert user_id == 123
        mock_client.get.assert_called_once_with("users/mine")

        # Second access should not trigger API call
        mock_client.get.reset_mock()
        user_id = base_ops.user_id
        assert user_id == 123
        mock_client.get.assert_not_called()

    def test_get_default_user_id(self):
        """Test getting default user ID through the public interface."""
        mock_client = Mock(spec=httpx.Client)
        mock_response = Mock()
        mock_response.json.return_value = {"Id": 456, "Name": "Test User"}
        mock_client.get.return_value = mock_response

        base_ops = BaseOperations(mock_client)
        # Test through public user_id property
        user_id = base_ops.user_id

        assert user_id == 456
        mock_client.get.assert_called_once_with("users/mine")
        mock_response.raise_for_status.assert_called_once()

    def test_get_default_user_id_error(self):
        """Test user_id property with API error."""
        mock_client = Mock(spec=httpx.Client)
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=Mock()
        )
        mock_client.get.return_value = mock_response

        base_ops = BaseOperations(mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            # Access through public property
            _ = base_ops.user_id
