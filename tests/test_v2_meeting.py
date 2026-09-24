"""Tests for the v2 (GraphQL) meeting operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.models import Meeting, MeetingListItem, User
from bloomy.v2.operations.meeting import AsyncMeetingOperations, MeetingOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

MEETING_LIST_NODE = {
    "id": 349524,
    "name": "v2 API",
    "meetingType": "L10",
    "createdTimestamp": 1790273635,
    "archived": False,
    "userIsAttendee": True,
    "isCurrentUserAdmin": False,
}

ATTENDEE_NODE = {
    "id": 1305290,
    "firstName": "Fran",
    "lastName": "Orozco",
    "fullName": "Fran Orozco",
    "avatar": None,
    "user": {"email": "fran@example.com"},
}

MEETING_DETAILS_DATA = {
    "id": 349524,
    "name": "v2 API",
    "orgId": 1305289,
    "meetingType": "L10",
    "createdTimestamp": 1790273635,
    "archived": False,
    "attendees": {"nodes": [ATTENDEE_NODE]},
}


def _response(json_data: object) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


class TestMeetingOperationsSync:
    """Tests for the sync `MeetingOperations`."""

    def test_list_defaults_to_current_user(self) -> None:
        """`list()` with no `user_id` fetches the authenticated user first."""
        client = Mock()
        ops = MeetingOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response(
                {
                    "data": {
                        "user": {"meetingsListLookup": {"nodes": [MEETING_LIST_NODE]}}
                    }
                }
            ),
        ]

        result = ops.list()

        assert len(result) == 1
        assert isinstance(result[0], MeetingListItem)
        assert result[0].id == 349524
        assert result[0].meeting_type == "L10"

    def test_list_explicit_user_id(self) -> None:
        """`list(user_id=...)` skips the current-user lookup."""
        client = Mock()
        ops = MeetingOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"user": {"meetingsListLookup": {"nodes": [MEETING_LIST_NODE]}}}}
        )

        result = ops.list(user_id=1305290)

        assert len(result) == 1
        client.post.assert_called_once()
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"userId": 1305290}

    def test_details_returns_meeting_with_attendees(self) -> None:
        """`details()` returns a `Meeting` with nested `User` attendees."""
        client = Mock()
        ops = MeetingOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": MEETING_DETAILS_DATA}}
        )

        result = ops.details(349524)

        assert isinstance(result, Meeting)
        assert result.id == 349524
        assert result.org_id == 1305289
        assert len(result.attendees) == 1
        assert isinstance(result.attendees[0], User)
        assert result.attendees[0].email == "fran@example.com"

    def test_details_raises_when_meeting_is_null(self) -> None:
        """`details()` raises `GraphQLError` when `meeting` is `null` (unknown id)."""
        client = Mock()
        ops = MeetingOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"meeting": None}})

        with pytest.raises(GraphQLError, match="Meeting 999999999 not found"):
            ops.details(999999999)

    def test_attendees_returns_users(self) -> None:
        """`attendees()` returns a flat list of `User` models."""
        client = Mock()
        ops = MeetingOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"attendees": {"nodes": [ATTENDEE_NODE]}}}}
        )

        result = ops.attendees(349524)

        assert len(result) == 1
        assert result[0].id == 1305290
        assert result[0].email == "fran@example.com"


class TestMeetingOperationsAsync:
    """Tests for the async `AsyncMeetingOperations`."""

    @pytest.mark.asyncio
    async def test_list_explicit_user_id(self) -> None:
        """`list(user_id=...)` skips the current-user lookup."""
        client = AsyncMock()
        ops = AsyncMeetingOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {"user": {"meetingsListLookup": {"nodes": [MEETING_LIST_NODE]}}}
        }
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.list(user_id=1305290)

        assert len(result) == 1
        assert result[0].id == 349524

    @pytest.mark.asyncio
    async def test_details_returns_meeting_with_attendees(self) -> None:
        """`details()` returns a `Meeting` with nested `User` attendees."""
        client = AsyncMock()
        ops = AsyncMeetingOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"meeting": MEETING_DETAILS_DATA}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.details(349524)

        assert isinstance(result, Meeting)
        assert len(result.attendees) == 1

    @pytest.mark.asyncio
    async def test_details_raises_when_meeting_is_null(self) -> None:
        """`details()` raises `GraphQLError` when `meeting` is `null`."""
        client = AsyncMock()
        ops = AsyncMeetingOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"meeting": None}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="Meeting 999999999 not found"):
            await ops.details(999999999)

    @pytest.mark.asyncio
    async def test_attendees_returns_users(self) -> None:
        """`attendees()` returns a flat list of `User` models."""
        client = AsyncMock()
        ops = AsyncMeetingOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {"meeting": {"attendees": {"nodes": [ATTENDEE_NODE]}}}
        }
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.attendees(349524)

        assert len(result) == 1
        assert result[0].id == 1305290
