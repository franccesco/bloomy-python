"""Base class for API operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .abstract_operations import AbstractOperations

if TYPE_CHECKING:
    import httpx


class BaseOperations(AbstractOperations):
    """Base class for all API operation classes."""

    def __init__(self, client: httpx.Client) -> None:
        """Initialize the operations class.

        Args:
            client: The HTTP client to use for API requests.

        """
        super().__init__(client)
        self._client: httpx.Client = client

    @property
    def user_id(self) -> int:
        """Get the current user's ID, fetching it if needed.

        Returns:
            The user ID of the authenticated user.

        """
        if self._user_id is None:
            self._user_id = self._get_default_user_id()
        return self._user_id

    def _get_default_user_id(self) -> int:
        """Fetch the default user ID from the API.

        Returns:
            The user ID of the authenticated user.

        """
        response = self._client.get("users/mine")
        response.raise_for_status()
        data = response.json()
        return data["Id"]
