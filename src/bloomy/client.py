"""Main client for interacting with the Bloom Growth API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from .configuration import Configuration
from .operations.goals import GoalOperations
from .operations.headlines import HeadlineOperations
from .operations.issues import IssueOperations
from .operations.meetings import MeetingOperations
from .operations.scorecard import ScorecardOperations
from .operations.todos import TodoOperations
from .operations.users import UserOperations

if TYPE_CHECKING:
    from typing import Any


class Client:
    """The Client class is the main entry point for interacting with the Bloomy API.

    It provides methods for managing Bloom Growth features.

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
        ```

    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize a new Client instance.

        Args:
            api_key: The API key to use. If not provided, will attempt to
                     load from environment variable (BG_API_KEY) or configuration file.

        Raises:
            ValueError: If no API key is provided or found in configuration.

        """
        # Use Configuration class which handles priority:
        # 1. Explicit api_key parameter
        # 2. BG_API_KEY environment variable
        # 3. Configuration file (~/.bloomy/config.yaml)
        self.configuration = Configuration(api_key)

        if not self.configuration.api_key:
            raise ValueError(
                "No API key provided. Set it explicitly, via BG_API_KEY "
                "environment variable, or in ~/.bloomy/config.yaml configuration file."
            )

        self._api_key = self.configuration.api_key
        self._base_url = "https://app.bloomgrowth.com/api/v1"

        # Initialize HTTP client
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            timeout=30.0,
        )

        # Initialize operation classes
        self.user = UserOperations(self._client)
        self.todo = TodoOperations(self._client)
        self.meeting = MeetingOperations(self._client)
        self.goal = GoalOperations(self._client)
        self.scorecard = ScorecardOperations(self._client)
        self.issue = IssueOperations(self._client)
        self.headline = HeadlineOperations(self._client)

    def __enter__(self) -> Client:
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
