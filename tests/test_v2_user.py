"""Tests for the v2 (GraphQL) user operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.models import User
from bloomy.v2.operations.user import AsyncUserOperations, UserOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

USER_NODE = {
    "id": 1305290,
    "firstName": "Fran",
    "lastName": "Orozco",
    "fullName": "Fran Orozco",
    "email": "fran@example.com",
    "avatar": None,
}


def _response(json_data: object) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


class TestUserOperationsSync:
    """Tests for the sync `UserOperations`."""

    def test_details_defaults_to_current_user(self) -> None:
        """`details()` with no `user_id` fetches the authenticated user."""
        client = Mock()
        ops = UserOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"user": USER_NODE}}),
        ]

        result = ops.details()

        assert isinstance(result, User)
        assert result.id == 1305290
        assert result.full_name == "Fran Orozco"
        assert result.email == "fran@example.com"

        second_call_variables = client.post.call_args_list[1].kwargs["json"][
            "variables"
        ]
        assert second_call_variables == {"id": 1305290}

    def test_details_explicit_user_id(self) -> None:
        """`details(user_id=...)` skips the current-user lookup."""
        client = Mock()
        ops = UserOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"user": USER_NODE}})

        result = ops.details(user_id=1305290)

        assert result.id == 1305290
        client.post.assert_called_once()

    def test_details_raises_when_user_is_null(self) -> None:
        """`details()` raises `GraphQLError` when `user` is `null` (unknown id)."""
        client = Mock()
        ops = UserOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"user": None}})

        with pytest.raises(GraphQLError, match="User 999999999 not found"):
            ops.details(user_id=999999999)

    def test_list_returns_all_users(self) -> None:
        """`list()` returns every user from the `users` connection."""
        client = Mock()
        ops = UserOperations(client, GRAPHQL_URL)
        other = {**USER_NODE, "id": 2, "fullName": "Scout Bloom"}
        client.post.return_value = _response(
            {"data": {"users": {"nodes": [USER_NODE, other]}}}
        )

        result = ops.list()

        assert len(result) == 2
        assert result[0].id == 1305290
        assert result[1].full_name == "Scout Bloom"


class TestUserOperationsAsync:
    """Tests for the async `AsyncUserOperations`."""

    @pytest.mark.asyncio
    async def test_details_defaults_to_current_user(self) -> None:
        """`details()` with no `user_id` fetches the authenticated user."""
        client = AsyncMock()
        ops = AsyncUserOperations(client, GRAPHQL_URL)
        response_id = MagicMock()
        response_id.status_code = 200
        response_id.json.return_value = {
            "data": {"getAuthenticatedUserId": {"id": 1305290}}
        }
        response_id.raise_for_status = MagicMock()

        response_user = MagicMock()
        response_user.status_code = 200
        response_user.json.return_value = {"data": {"user": USER_NODE}}
        response_user.raise_for_status = MagicMock()

        client.post.side_effect = [response_id, response_user]

        result = await ops.details()

        assert isinstance(result, User)
        assert result.id == 1305290

    @pytest.mark.asyncio
    async def test_details_raises_when_user_is_null(self) -> None:
        """`details()` raises `GraphQLError` when `user` is `null`."""
        client = AsyncMock()
        ops = AsyncUserOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"user": None}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="User 999999999 not found"):
            await ops.details(user_id=999999999)

    @pytest.mark.asyncio
    async def test_list_returns_all_users(self) -> None:
        """`list()` returns every user from the `users` connection."""
        client = AsyncMock()
        ops = AsyncUserOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"users": {"nodes": [USER_NODE]}}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.list()

        assert len(result) == 1
        assert result[0].id == 1305290
