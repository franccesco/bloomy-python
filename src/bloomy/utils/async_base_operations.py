"""Async base class for API operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_operations import AbstractOperations

if TYPE_CHECKING:
    import httpx


class AsyncBaseOperations(AbstractOperations):
    """Async base class for all API operation classes."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Initialize the async operations class.

        Args:
            client: The async HTTP client to use for API requests.

        """
        super().__init__(client)
        self._client: httpx.AsyncClient = client

    @property
    def user_id(self) -> int:
        """Get/set the user ID.

        For async operations, use get_user_id() to fetch from API.

        Raises:
            RuntimeError: If the user ID is not set. Use get_user_id() to fetch from
                API.

        """
        if self._user_id is None:
            raise RuntimeError("User ID not set. Use get_user_id() to fetch from API.")
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        """Set the user ID."""
        self._user_id = value

    async def get_user_id(self) -> int:
        """Get the current user's ID, fetching it if needed.

        Returns:
            The user ID of the authenticated user.

        """
        if self._user_id is None:
            self._user_id = await self._get_default_user_id()
        return self._user_id

    async def _get_default_user_id(self) -> int:
        """Fetch the default user ID from the API.

        Returns:
            The user ID of the authenticated user.

        """
        response = await self._client.get("users/mine")
        response.raise_for_status()
        data = response.json()
        return data["Id"]
