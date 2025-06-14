"""Tests for the Configuration module."""

import os
from pathlib import Path
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

        with pytest.raises(ConfigurationError) as exc_info:
            config._store_api_key()

        assert "API key is None" in str(exc_info.value)

    def test_load_api_key_no_file(self):
        """Test loading API key when config file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            config = Configuration()
            result = config._load_api_key()
            assert result is None

    def test_load_api_key_invalid_yaml(self):
        """Test loading API key with invalid YAML."""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch("pathlib.Path.exists", return_value=True):
                config = Configuration()
                result = config._load_api_key()
                assert result is None

    def test_config_paths(self):
        """Test configuration directory and file paths."""
        config = Configuration()

        assert config._config_dir == Path.home() / ".bloomy"
        assert config._config_file == Path.home() / ".bloomy" / "config.yaml"
