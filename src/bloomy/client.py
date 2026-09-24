"""Main client for interacting with the Bloom Growth API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from urllib.parse import urlsplit

import httpx

from .configuration import Configuration
from .exceptions import ConfigurationError
from .v1 import V1
from .v2 import V2

if TYPE_CHECKING:
    from typing import Any


class Client:
    """The Client class is the main entry point for interacting with the Bloomy API.

    It provides methods for managing Bloom Growth features.

    `client.v1` groups the REST API operations (`user`, `todo`, `meeting`,
    `goal`, `scorecard`, `issue`, `headline`); the top-level attributes below
    are aliases of `client.v1.*`, kept for backward compatibility.
    `client.v2` groups the GraphQL API operations (`user`, `meeting`,
    `issue`, ...).

    Example:
        ```python
        from bloomy import Client
        client = Client()
        client.meeting.list()
        client.user.details()
        client.meeting.delete(123)
        client.scorecard.list()
        client.issue.list()
        client.headline.list()

        # v2 (GraphQL)
        client.v2.user.details()
        client.v2.meeting.details(349524)
        client.v2.issue.list(349524)
        ```

    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://app.bloomgrowth.com/api/v1",
        timeout: float = 30.0,
        graphql_url: str | None = None,
    ) -> None:
        """Initialize a new Client instance.

        Args:
            api_key: The API key to use. If not provided, will attempt to
                     load from environment variable (BG_API_KEY) or configuration file.
            base_url: The base URL for the API. Defaults to the production API URL.
            timeout: The timeout in seconds for HTTP requests. Defaults to 30.0.
            graphql_url: The absolute URL of the v2 GraphQL endpoint. Defaults to
                the scheme and host of `base_url` plus `/graphql/`.

        Raises:
            ConfigurationError: If no API key is provided or found in configuration.

        """
        # Use Configuration class which handles priority:
        # 1. Explicit api_key parameter
        # 2. BG_API_KEY environment variable
        # 3. Configuration file (~/.bloomy/config.yaml)
        self.configuration = Configuration(api_key)

        if not self.configuration.api_key:
            raise ConfigurationError(
                "No API key provided. Set it explicitly, via BG_API_KEY "
                "environment variable, or in ~/.bloomy/config.yaml configuration file."
            )

        self._api_key = self.configuration.api_key
        self._base_url = base_url

        if graphql_url is None:
            parsed = urlsplit(base_url)
            graphql_url = f"{parsed.scheme}://{parsed.netloc}/graphql/"
        self._graphql_url = graphql_url

        # Initialize HTTP client
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            timeout=timeout,
        )

        # Initialize the v1 (REST) and v2 (GraphQL) operation namespaces,
        # sharing the same httpx client (v2 requests pass an absolute URL,
        # which overrides the client's base_url).
        self.v1 = V1(self._client)
        self.v2 = V2(self._client, self._graphql_url)

        # Top-level attributes are aliases of `self.v1.*` (same objects),
        # kept for backward compatibility.
        self.user = self.v1.user
        self.todo = self.v1.todo
        self.meeting = self.v1.meeting
        self.goal = self.v1.goal
        self.scorecard = self.v1.scorecard
        self.issue = self.v1.issue
        self.headline = self.v1.headline

    def __enter__(self) -> Self:
        """Context manager entry.

        Returns:
            The client instance.

        """
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - close the HTTP client."""
        self._client.close()

    def close(self) -> None:
        """Close the HTTP client connection."""
        self._client.close()
