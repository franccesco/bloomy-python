"""Configuration management for the Bloomy SDK."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
import yaml

from .exceptions import AuthenticationError, ConfigurationError

if TYPE_CHECKING:
    pass


class Configuration:
    """The Configuration class is responsible for managing authentication."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize a new Configuration instance.

        Args:
            api_key: Optional API key. If not provided, will attempt to load from
                     environment variable or configuration file.

        Example:
            ```python
            config = Bloomy.Configuration(api_key)
            ```

        """
        self.api_key = api_key or os.environ.get("BG_API_KEY") or self._load_api_key()

    def configure_api_key(
        self, username: str, password: str, store_key: bool = False
    ) -> None:
        """Configure the API key using the provided username and password.

        Args:
            username: The username for authentication
            password: The password for authentication
            store_key: Whether to store the API key (default: False)

        Note:
            This method only fetches and stores the API key if it is currently None.
            It saves the key under '~/.bloomy/config.yaml' if 'store_key: True' is
            passed.

        Example:
            ```python
            config.configure_api_key("user", "pass", store_key=True)
            config.api_key
            # Returns: 'xxxx...'
            ```

        """
        self.api_key = self._fetch_api_key(username, password)
        if store_key:
            self._store_api_key()

    def _fetch_api_key(self, username: str, password: str) -> str:
        """Fetch the API key using the provided username and password.

        Args:
            username: The username for authentication
            password: The password for authentication

        Returns:
            The fetched API key

        Raises:
            AuthenticationError: If authentication fails

        """
        with httpx.Client() as client:
            response = client.post(
                "https://app.bloomgrowth.com/Token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                content=urlencode(
                    {
                        "grant_type": "password",
                        "userName": username,
                        "password": password,
                    }
                ),
            )

        if not response.is_success:
            raise AuthenticationError(
                f"Failed to fetch API key: {response.status_code} - {response.text}"
            )

        data = response.json()
        return data["access_token"]

    def _store_api_key(self) -> None:
        """Store the API key in a local configuration file.

        Raises:
            ConfigurationError: If the API key is None

        """
        if self.api_key is None:
            raise ConfigurationError("API key is None")

        config_file = self._config_file
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config_data = {"version": 1, "api_key": self.api_key}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

    def _load_api_key(self) -> str | None:
        """Load the API key from a local configuration file.

        Returns:
            The loaded API key or None if the file does not exist

        """
        config_file = self._config_file
        if not config_file.exists():
            return None

        try:
            with open(config_file) as f:
                data = yaml.safe_load(f)
                return data.get("api_key")
        except Exception:
            return None

    @property
    def _config_dir(self) -> Path:
        """Return the directory path for the configuration file."""
        return Path.home() / ".bloomy"

    @property
    def _config_file(self) -> Path:
        """Return the file path for the configuration file."""
        return self._config_dir / "config.yaml"
