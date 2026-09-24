"""User operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins

from ..base import AsyncGraphQLOperations, GraphQLOperations, dig_nodes
from ..models import User

_USER_FIELDS = "id firstName lastName fullName email avatar"


class UserOperationsMixin:
    """GraphQL documents shared by user operations."""

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
        return User.model_validate(
            self._one(data, "user", label="User", entity_id=user_id)
        )

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
        return [User.model_validate(node) for node in dig_nodes(data, "users")]


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
        return User.model_validate(
            self._one(data, "user", label="User", entity_id=user_id)
        )

    async def list(self) -> builtins.list[User]:
        """List every user in the organization.

        Returns:
            A list of `User` model instances, ordered by full name.

        """
        data = await self._execute(self._USER_LIST_QUERY)
        return [User.model_validate(node) for node in dig_nodes(data, "users")]
