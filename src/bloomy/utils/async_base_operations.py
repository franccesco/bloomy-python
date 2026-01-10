"""Async base class for API operations."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from ..models import BulkCreateError, BulkCreateResult
from .abstract_operations import AbstractOperations

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

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

    async def _process_bulk_async[T](
        self,
        items: list[dict[str, Any]],
        create_func: Callable[[dict[str, Any]], Awaitable[T]],
        required_fields: list[str],
        max_concurrent: int = 5,
    ) -> BulkCreateResult[T]:
        """Process bulk creation asynchronously with concurrency control.

        Args:
            items: List of item data dictionaries.
            create_func: Async function to create a single item from data dict.
            required_fields: List of required field names.
            max_concurrent: Maximum number of concurrent API requests.

        Returns:
            BulkCreateResult with successful and failed items.

        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def create_single(
            index: int, item_data: dict[str, Any]
        ) -> tuple[int, T | BulkCreateError]:
            async with semaphore:
                try:
                    self._validate_bulk_item(item_data, required_fields)
                    created = await create_func(item_data)
                    return (index, created)
                except Exception as e:
                    error = BulkCreateError(
                        index=index, input_data=item_data, error=str(e)
                    )
                    return (index, error)

        tasks = [
            create_single(index, item_data) for index, item_data in enumerate(items)
        ]
        results = await asyncio.gather(*tasks)
        results_list = list(results)
        results_list.sort(key=lambda x: x[0])

        successful: list[T] = []
        failed: list[BulkCreateError] = []

        for _, result in results_list:
            if isinstance(result, BulkCreateError):
                failed.append(result)
            else:
                successful.append(result)

        return BulkCreateResult(successful=successful, failed=failed)
