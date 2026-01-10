"""Abstract base classes and protocols for operations."""

from __future__ import annotations

from typing import Any

from ..models import BulkCreateError, BulkCreateResult


class AbstractOperations:
    """Abstract base class for shared logic between sync and async operations."""

    def __init__(self, client: Any) -> None:
        """Initialize the operations class.

        Args:
            client: The HTTP client to use for API requests.

        """
        self._client = client
        self._user_id: int | None = None

    def _prepare_params(self, **kwargs: Any) -> dict[str, Any]:
        """Prepare request parameters by removing None values.

        Args:
            **kwargs: The parameters to prepare.

        Returns:
            A dictionary with None values removed.

        """
        return {k: v for k, v in kwargs.items() if v is not None}

    def _validate_mutual_exclusion(
        self, param1: Any | None, param2: Any | None, param1_name: str, param2_name: str
    ) -> None:
        """Validate that two parameters are mutually exclusive.

        Args:
            param1: The first parameter value.
            param2: The second parameter value.
            param1_name: The name of the first parameter.
            param2_name: The name of the second parameter.

        Raises:
            ValueError: If both parameters are provided.

        """
        if param1 is not None and param2 is not None:
            raise ValueError(f"Cannot specify both {param1_name} and {param2_name}")

    def _validate_bulk_item(
        self, item_data: dict[str, Any], required_fields: list[str]
    ) -> None:
        """Validate that required fields are present in bulk item data.

        Args:
            item_data: The item data dictionary to validate.
            required_fields: List of required field names.

        Raises:
            ValueError: If any required field is missing.

        """
        for field in required_fields:
            if item_data.get(field) is None:
                raise ValueError(f"{field} is required")

    def _process_bulk_sync[T](
        self,
        items: list[dict[str, Any]],
        create_func: Any,
        required_fields: list[str],
    ) -> BulkCreateResult[T]:
        """Process bulk creation synchronously.

        Args:
            items: List of item data dictionaries.
            create_func: Function to create a single item from data dict.
            required_fields: List of required field names.

        Returns:
            BulkCreateResult with successful and failed items.

        """
        successful: list[T] = []
        failed: list[BulkCreateError] = []

        for index, item_data in enumerate(items):
            try:
                self._validate_bulk_item(item_data, required_fields)
                created = create_func(item_data)
                successful.append(created)
            except Exception as e:
                failed.append(
                    BulkCreateError(index=index, input_data=item_data, error=str(e))
                )

        return BulkCreateResult(successful=successful, failed=failed)
