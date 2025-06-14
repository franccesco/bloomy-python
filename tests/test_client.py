"""Tests for the Client module."""

from unittest.mock import Mock, patch

import pytest

from bloomy import Client


class TestClient:
    """Test cases for the Client class."""

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")
            assert client._api_key == "test-key"

    def test_init_without_api_key(self):
        """Test client initialization without API key."""
        with patch("bloomy.client.Configuration") as mock_config_class:
            mock_config = Mock()
            mock_config.api_key = "config-key"
            mock_config_class.return_value = mock_config

            with patch("bloomy.client.httpx.Client"):
                client = Client()
                assert client._api_key == "config-key"

    def test_init_no_api_key_found(self):
        """Test client initialization with no API key available."""
        with patch("bloomy.client.Configuration") as mock_config_class:
            mock_config = Mock()
            mock_config.api_key = None
            mock_config_class.return_value = mock_config

            with pytest.raises(ValueError) as exc_info:
                Client()

            assert "No API key provided" in str(exc_info.value)

    def test_http_client_initialization(self):
        """Test HTTP client is initialized correctly."""
        with patch("bloomy.client.httpx.Client") as mock_client_class:
            Client(api_key="test-key")

            mock_client_class.assert_called_once_with(
                base_url="https://app.bloomgrowth.com/api/v1",
                headers={
                    "Accept": "*/*",
                    "Content-Type": "application/json",
                    "Authorization": "Bearer test-key",
                },
                timeout=30.0,
            )

    def test_operations_initialization(self):
        """Test all operation classes are initialized."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")

            # Check all operations are initialized
            assert hasattr(client, "user")
            assert hasattr(client, "todo")
            assert hasattr(client, "goal")
            assert hasattr(client, "meeting")
            assert hasattr(client, "scorecard")
            assert hasattr(client, "issue")
            assert hasattr(client, "headline")

    def test_context_manager(self):
        """Test client works as a context manager."""
        with patch("bloomy.client.httpx.Client") as mock_client_class:
            mock_http_client = Mock()
            mock_client_class.return_value = mock_http_client

            with Client(api_key="test-key") as client:
                assert isinstance(client, Client)

            # Check HTTP client was closed
            mock_http_client.close.assert_called_once()

    def test_close_method(self):
        """Test client close method."""
        with patch("bloomy.client.httpx.Client") as mock_client_class:
            mock_http_client = Mock()
            mock_client_class.return_value = mock_http_client

            client = Client(api_key="test-key")
            client.close()

            mock_http_client.close.assert_called_once()

    def test_base_url(self):
        """Test the base URL is set correctly."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")
            assert client._base_url == "https://app.bloomgrowth.com/api/v1"
