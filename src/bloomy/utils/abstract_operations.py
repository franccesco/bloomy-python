"""Abstract base classes and protocols for operations."""

from __future__ import annotations

from typing import Any


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
