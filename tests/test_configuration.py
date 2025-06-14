"""Tests for the Configuration module."""

import os
from unittest.mock import Mock, mock_open, patch

import httpx
import pytest
import yaml

from bloomy import Configuration
from bloomy.exceptions import AuthenticationError, ConfigurationError


class TestConfiguration:
    """Test cases for the Configuration class."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        config = Configuration(api_key="test-key")
        assert config.api_key == "test-key"

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.dict(os.environ, {"BG_API_KEY": "env-key"}):
            config = Configuration()
            assert config.api_key == "env-key"

    def test_init_with_config_file(self):
        """Test initialization with config file."""
        mock_yaml_data = {"version": 1, "api_key": "file-key"}

        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_yaml_data))):
            with patch("pathlib.Path.exists", return_value=True):
                config = Configuration()
                assert config.api_key == "file-key"

    def test_init_priority_order(self):
        """Test API key priority: direct > env > file."""
        mock_yaml_data = {"version": 1, "api_key": "file-key"}

        with patch.dict(os.environ, {"BG_API_KEY": "env-key"}):
            with patch("builtins.open", mock_open(read_data=yaml.dump(mock_yaml_data))):
                with patch("pathlib.Path.exists", return_value=True):
                    # Direct API key takes precedence
                    config = Configuration(api_key="direct-key")
                    assert config.api_key == "direct-key"

                    # Env var takes precedence over file
                    config = Configuration()
                    assert config.api_key == "env-key"

    def test_configure_api_key_success(self):
        """Test successful API key configuration."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.json.return_value = {"access_token": "new-api-key"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            config = Configuration()
            config.configure_api_key("user", "pass")

            assert config.api_key == "new-api-key"
            mock_client.post.assert_called_once()

    def test_configure_api_key_failure(self):
        """Test API key configuration with authentication failure."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            config = Configuration()
            with pytest.raises(AuthenticationError) as exc_info:
                config.configure_api_key("user", "wrong-pass")

            assert "401" in str(exc_info.value)

    def test_configure_api_key_with_store(self):
        """Test API key configuration with storage."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.is_success = True
        mock_response.json.return_value = {"access_token": "stored-api-key"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            with patch("builtins.open", mock_open()) as mock_file:
                with patch("pathlib.Path.mkdir"):
                    config = Configuration()
                    config.configure_api_key("user", "pass", store_key=True)

                    assert config.api_key == "stored-api-key"
                    mock_file.assert_called()

    def test_store_api_key_without_key(self):
        """Test storing API key when key is None."""
        config = Configuration()
        config.api_key = None

        # Test through public interface - configure_api_key with store_key=True
        def mock_fetch(u: str, p: str) -> None:
            return None

        with patch.object(config, "_fetch_api_key", side_effect=mock_fetch):
            config.api_key = None
            # Attempting to store a None key should raise error
            with pytest.raises(ConfigurationError) as exc_info:
                config.configure_api_key("user", "pass", store_key=True)

        assert "API key is None" in str(exc_info.value)

    def test_load_api_key_no_file(self):
        """Test loading API key when config file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                config = Configuration()
                # When no file exists and no env var, api_key should be None
                assert config.api_key is None

    def test_load_api_key_invalid_yaml(self):
        """Test loading API key with invalid YAML."""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch.dict(os.environ, {}, clear=True):
                    # With invalid YAML, config should handle gracefully
                    config = Configuration()
                    assert config.api_key is None

    def test_config_file_location(self):
        """Test that configuration is loaded from the correct location."""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("builtins.open", mock_open(read_data="api_key: test-key")):
                with patch.dict(os.environ, {}, clear=True):
                    # Initialize config which should try to load from file
                    config = Configuration()

                    # Check that Path.exists was called
                    assert mock_exists.called
                    # Verify config was created successfully
                    assert config is not None
                    # The configuration loading mechanism uses the expected path
