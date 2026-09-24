"""User operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import AsyncGraphQLOperations, GraphQLOperations
from ..models import User


class UserOperationsMixin:
    """Shared GraphQL documents and response transforms for user operations."""

    _USER_FIELDS = "id firstName lastName fullName email avatar"

    _USER_DETAILS_QUERY = f"""
    query($id: Long!) {{
      user(id: $id) {{
        {_USER_FIELDS}
      }}
    }}
    """

    _USER_LIST_QUERY = f"""
    query {{
      users(order: [{{ fullName: ASC }}]) {{
        nodes {{
          {_USER_FIELDS}
        }}
      }}
    }}
    """

    def _transform_user(self, data: dict[str, Any]) -> User:
        """Transform a raw GraphQL user object into a `User` model.

        Returns:
            A `User` model instance.

        """
        return User(**data)


class UserOperations(GraphQLOperations, UserOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to users."""

    def details(self, user_id: int | None = None) -> User:
        """Get details for a user.

        Args:
            user_id: The ID of the user (defaults to the current user).

        Returns:
            A `User` model instance.

        Example:
            ```python
            client.v2.user.details()
            # Returns: User(id=1, first_name='John', last_name='Doe', ...)
            ```

        """
        if user_id is None:
            user_id = self.user_id

        data = self._execute(self._USER_DETAILS_QUERY, {"id": user_id})
        return self._transform_user(self._require_entity(data, "user", user_id, "User"))

    def list(self) -> builtins.list[User]:
        """List every user in the organization.

        Returns:
            A list of `User` model instances, ordered by full name.

        Example:
            ```python
            client.v2.user.list()
            # Returns: [User(id=1, full_name='John Doe', ...), ...]
            ```

        """
        data = self._execute(self._USER_LIST_QUERY)
        return [self._transform_user(node) for node in data["users"]["nodes"]]


class AsyncUserOperations(AsyncGraphQLOperations, UserOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to users."""

    async def details(self, user_id: int | None = None) -> User:
        """Get details for a user.

        Args:
            user_id: The ID of the user (defaults to the current user).

        Returns:
            A `User` model instance.

        """
        if user_id is None:
            user_id = await self.get_user_id()

        data = await self._execute(self._USER_DETAILS_QUERY, {"id": user_id})
        return self._transform_user(self._require_entity(data, "user", user_id, "User"))

    async def list(self) -> builtins.list[User]:
        """List every user in the organization.

        Returns:
            A list of `User` model instances, ordered by full name.

        """
        data = await self._execute(self._USER_LIST_QUERY)
        return [self._transform_user(node) for node in data["users"]["nodes"]]
