"""Asynchronous client for the Bloomy API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import httpx

from .configuration import Configuration
from .exceptions import ConfigurationError

if TYPE_CHECKING:
    from types import TracebackType

    from .operations.async_ import (
        AsyncGoalOperations,
        AsyncHeadlineOperations,
        AsyncIssueOperations,
        AsyncMeetingOperations,
        AsyncScorecardOperations,
        AsyncTodoOperations,
        AsyncUserOperations,
    )
    from .v1 import AsyncV1
    from .v2 import AsyncV2


class AsyncClient:
    """Asynchronous client for interacting with the Bloomy API.

    This client provides async access to all Bloomy API operations including
    users, meetings, todos, goals, headlines, issues, and scorecards.

    `client.v1` groups the REST API operations; the top-level attributes are
    aliases of `client.v1.*`, kept for backward compatibility. `client.v2`
    groups the GraphQL API operations (`user`, `meeting`, `issue`, ...).

    Args:
        api_key: The API key for authentication. If not provided, it will be loaded
            from environment variables or configuration files.
        base_url: The base URL for the API. Defaults to the production API URL.

    Example:
        Using the async client with context manager:

        ```python
        import asyncio
        from bloomy import AsyncClient

        async def main():
            async with AsyncClient(api_key="your-api-key") as client:
                user = await client.user.details()
                print(user.name)

        asyncio.run(main())
        ```

        Without context manager:

        ```python
        client = AsyncClient(api_key="your-api-key")
        user = await client.user.details()
        await client.close()
        ```

    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://app.bloomgrowth.com/api/v1",
        timeout: float = 30.0,
        graphql_url: str | None = None,
    ) -> None:
        """Initialize the async Bloomy client.

        Args:
            api_key: The API key for authentication.
            base_url: The base URL for the API.
            timeout: The timeout in seconds for HTTP requests. Defaults to 30.0.
            graphql_url: The absolute URL of the v2 GraphQL endpoint. Defaults to
                the scheme and host of `base_url` plus `/graphql/`.

        Raises:
            ConfigurationError: If no API key is provided or found in configuration.

        """
        config = Configuration(api_key=api_key)

        if not config.api_key:
            raise ConfigurationError(
                "No API key provided. Set it explicitly, via BG_API_KEY "
                "environment variable, or in ~/.bloomy/config.yaml configuration file."
            )

        # Lazy imports to avoid circular dependencies
        from .v1 import AsyncV1
        from .v2 import AsyncV2, default_graphql_url

        if graphql_url is None:
            graphql_url = default_graphql_url(base_url)
        self._graphql_url = graphql_url

        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

        # Initialize the v1 (REST) and v2 (GraphQL) operation namespaces,
        # sharing the same httpx client (v2 requests pass an absolute URL,
        # which overrides the client's base_url).
        self.v1: AsyncV1 = AsyncV1(self._client)
        self.v2: AsyncV2 = AsyncV2(self._client, self._graphql_url)

        # Top-level attributes are aliases of `self.v1.*` (same objects),
        # kept for backward compatibility.
        self.user: AsyncUserOperations = self.v1.user
        self.meeting: AsyncMeetingOperations = self.v1.meeting
        self.todo: AsyncTodoOperations = self.v1.todo
        self.goal: AsyncGoalOperations = self.v1.goal
        self.headline: AsyncHeadlineOperations = self.v1.headline
        self.issue: AsyncIssueOperations = self.v1.issue
        self.scorecard: AsyncScorecardOperations = self.v1.scorecard

    async def __aenter__(self) -> Self:
        """Enter the async context manager.

        Returns:
            The async client instance.

        """
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager."""
        await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
