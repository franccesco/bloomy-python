"""Asynchronous client for the Bloomy API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from .configuration import Configuration

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


class AsyncClient:
    """Asynchronous client for interacting with the Bloomy API.

    This client provides async access to all Bloomy API operations including
    users, meetings, todos, goals, headlines, issues, and scorecards.

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
    ) -> None:
        """Initialize the async Bloomy client.

        Args:
            api_key: The API key for authentication.
            base_url: The base URL for the API.

        """
        config = Configuration(api_key=api_key)
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        # Lazy imports to avoid circular dependencies
        from .operations.async_.goals import AsyncGoalOperations
        from .operations.async_.headlines import AsyncHeadlineOperations
        from .operations.async_.issues import AsyncIssueOperations
        from .operations.async_.meetings import AsyncMeetingOperations
        from .operations.async_.scorecard import AsyncScorecardOperations
        from .operations.async_.todos import AsyncTodoOperations
        from .operations.async_.users import AsyncUserOperations

        self.user: AsyncUserOperations = AsyncUserOperations(self._client)
        self.meeting: AsyncMeetingOperations = AsyncMeetingOperations(self._client)
        self.todo: AsyncTodoOperations = AsyncTodoOperations(self._client)
        self.goal: AsyncGoalOperations = AsyncGoalOperations(self._client)
        self.headline: AsyncHeadlineOperations = AsyncHeadlineOperations(self._client)
        self.issue: AsyncIssueOperations = AsyncIssueOperations(self._client)
        self.scorecard: AsyncScorecardOperations = AsyncScorecardOperations(
            self._client
        )

    async def __aenter__(self) -> AsyncClient:
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
