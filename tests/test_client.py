"""Tests for the Client module."""

from unittest.mock import Mock, patch

import pytest

from bloomy import AsyncClient, Client
from bloomy.exceptions import ConfigurationError


class TestClient:
    """Test cases for the Client class."""

    def test_init_with_api_key(self):
        """Test client initialization with API key."""
        with patch("bloomy.client.httpx.Client") as mock_httpx:
            client = Client(api_key="test-key")
            assert isinstance(client, Client)
            # Test that httpx.Client was called with correct headers
            mock_httpx.assert_called_once()
            call_kwargs = mock_httpx.call_args.kwargs
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"

    def test_init_without_api_key(self):
        """Test client initialization without API key."""
        with patch("bloomy.client.Configuration") as mock_config_class:
            mock_config = Mock()
            mock_config.api_key = "config-key"
            mock_config_class.return_value = mock_config

            with patch("bloomy.client.httpx.Client") as mock_httpx:
                client = Client()
                assert isinstance(client, Client)
                # Test that configuration was used
                mock_config_class.assert_called_once()
                # Test that httpx.Client was called with config key
                call_kwargs = mock_httpx.call_args.kwargs
                assert call_kwargs["headers"]["Authorization"] == "Bearer config-key"

    def test_init_no_api_key_found(self):
        """Test client initialization with no API key available."""
        with patch("bloomy.client.Configuration") as mock_config_class:
            mock_config = Mock()
            mock_config.api_key = None
            mock_config_class.return_value = mock_config

            with pytest.raises(ConfigurationError) as exc_info:
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
        with patch("bloomy.client.httpx.Client") as mock_httpx:
            client = Client(api_key="test-key")
            assert isinstance(client, Client)
            # Test that httpx.Client was called with correct base_url
            call_kwargs = mock_httpx.call_args.kwargs
            assert call_kwargs["base_url"] == "https://app.bloomgrowth.com/api/v1"

    def test_custom_base_url(self):
        """Test client initialization with custom base URL."""
        with patch("bloomy.client.httpx.Client") as mock_httpx:
            custom_url = "https://custom.example.com/api"
            client = Client(api_key="test-key", base_url=custom_url)
            assert isinstance(client, Client)
            # Test that httpx.Client was called with custom base_url
            call_kwargs = mock_httpx.call_args.kwargs
            assert call_kwargs["base_url"] == custom_url

    def test_custom_timeout(self):
        """Test client initialization with custom timeout."""
        with patch("bloomy.client.httpx.Client") as mock_httpx:
            custom_timeout = 60.0
            client = Client(api_key="test-key", timeout=custom_timeout)
            assert isinstance(client, Client)
            # Test that httpx.Client was called with custom timeout
            call_kwargs = mock_httpx.call_args.kwargs
            assert call_kwargs["timeout"] == custom_timeout

    def test_custom_base_url_and_timeout(self):
        """Test client initialization with both custom base URL and timeout."""
        with patch("bloomy.client.httpx.Client") as mock_httpx:
            custom_url = "https://staging.example.com/api"
            custom_timeout = 45.0
            client = Client(
                api_key="test-key", base_url=custom_url, timeout=custom_timeout
            )
            assert isinstance(client, Client)
            # Test that httpx.Client was called with both custom values
            call_kwargs = mock_httpx.call_args.kwargs
            assert call_kwargs["base_url"] == custom_url
            assert call_kwargs["timeout"] == custom_timeout


class TestAsyncClient:
    """Test cases for the AsyncClient class."""

    def test_init_no_api_key_found(self):
        """Test async client initialization with no API key available."""
        with patch("bloomy.async_client.Configuration") as mock_config_class:
            mock_config = Mock()
            mock_config.api_key = None
            mock_config_class.return_value = mock_config

            with pytest.raises(ConfigurationError) as exc_info:
                AsyncClient()

            assert "No API key provided" in str(exc_info.value)

    def test_init_with_api_key(self):
        """Test async client initialization with API key."""
        with patch("bloomy.async_client.httpx.AsyncClient") as mock_httpx:
            client = AsyncClient(api_key="test-key")
            assert isinstance(client, AsyncClient)
            # Test that httpx.AsyncClient was called with correct headers
            mock_httpx.assert_called_once()
            call_kwargs = mock_httpx.call_args.kwargs
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
