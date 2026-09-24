"""Tests for the v2 (GraphQL) headline operations."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.models import Headline
from bloomy.v2.operations.headline import AsyncHeadlineOperations, HeadlineOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

HEADLINE_NODE = {
    "id": 987654,
    "title": "SDK v2 test headline",
    "recurrenceId": 349524,
    "notesId": "pad-1",
    "notesText": "some notes\n",
    "localHtml": None,
    "collaborationEnabled": True,
    "archived": False,
    "archivedTimestamp": None,
    "dateCreated": 1790275733,
    "assignee": {"id": 1305290, "fullName": "Fran Orozco"},
    "meeting": {"id": 349524, "name": "v2 API"},
}


def _response(json_data: object, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


def _async_response(json_data: object, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


class TestHeadlineOperationsSync:
    """Tests for the sync `HeadlineOperations`."""

    def test_details(self) -> None:
        """`details()` returns a transformed `Headline`, including plain-text notes."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"headline": HEADLINE_NODE}})

        result = ops.details(987654)

        assert isinstance(result, Headline)
        assert result.id == 987654
        assert result.owner is not None and result.owner.id == 1305290
        assert result.meeting is not None and result.meeting.id == 349524
        assert result.notes == "some notes"

    def test_details_with_null_assignee(self) -> None:
        """A headline with a `null` `assignee` produces `owner=None`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        node = {**HEADLINE_NODE, "assignee": None}
        client.post.return_value = _response({"data": {"headline": node}})

        result = ops.details(987654)

        assert result.owner is None

    def test_list_both_meeting_and_user_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="not both"):
            ops.list(meeting_id=349524, user_id=1305290)

    def test_list_by_meeting_open_only(self) -> None:
        """`list(meeting_id=...)` queries `meeting.headlines` (open only) by default."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"headlines": {"nodes": [HEADLINE_NODE]}}}}
        )

        result = ops.list(meeting_id=349524)

        assert len(result) == 1
        assert client.post.call_count == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"meetingId": 349524}

    def test_list_by_meeting_include_archived_merges(self) -> None:
        """`list(meeting_id=..., include_archived=True)` merges `archivedHeadlines`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        archived_node = {**HEADLINE_NODE, "id": 999, "archived": True}
        client.post.side_effect = [
            _response({"data": {"meeting": {"headlines": {"nodes": [HEADLINE_NODE]}}}}),
            _response(
                {"data": {"meeting": {"archivedHeadlines": {"nodes": [archived_node]}}}}
            ),
        ]

        result = ops.list(meeting_id=349524, include_archived=True)

        assert client.post.call_count == 2
        assert {headline.id for headline in result} == {987654, 999}
        second_query = client.post.call_args_list[1].kwargs["json"]["query"]
        assert "archivedHeadlines" in second_query

    def test_list_by_user_filters_archived_client_side(self) -> None:
        """`list(user_id=...)` drops archived headlines client-side by default.

        The root `headlines(userId)` connection includes archived headlines
        with no server-side filter applied here, so `list()` filters them out
        itself unless `include_archived=True`.
        """
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        archived_node = {**HEADLINE_NODE, "id": 999, "archived": True}
        client.post.return_value = _response(
            {"data": {"headlines": {"nodes": [HEADLINE_NODE, archived_node]}}}
        )

        result = ops.list(user_id=1305290)

        assert len(result) == 1
        assert result[0].id == 987654
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"userId": 1305290}

    def test_list_by_user_include_archived_keeps_all(self) -> None:
        """`list(user_id=..., include_archived=True)` keeps archived headlines."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        archived_node = {**HEADLINE_NODE, "id": 999, "archived": True}
        client.post.return_value = _response(
            {"data": {"headlines": {"nodes": [HEADLINE_NODE, archived_node]}}}
        )

        result = ops.list(user_id=1305290, include_archived=True)

        assert {headline.id for headline in result} == {987654, 999}

    def test_list_defaults_to_current_user(self) -> None:
        """`list()` with neither id given fetches headlines for the current user."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"headlines": {"nodes": [HEADLINE_NODE]}}}),
        ]

        result = ops.list()

        assert len(result) == 1
        variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert variables == {"userId": 1305290}

    def test_create_without_notes(self) -> None:
        """`create()` without notes skips `CreateNote` and reads back details."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = ops.create(349524, "SDK v2 test headline", user_id=1305290)

        assert result.id == 987654
        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables == {
            "input": {
                "title": "SDK v2 test headline",
                "assignee": 1305290,
                "meetings": [349524],
            }
        }

    def test_create_with_notes_calls_create_note_first(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateHeadline`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-99"}}}),
            _response({"data": {"CreateHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        ops.create(349524, "SDK v2 test headline", user_id=1305290, notes="hello")

        create_headline_variables = client.post.call_args_list[1].kwargs["json"][
            "variables"
        ]
        assert create_headline_variables["input"]["notesId"] == "pad-99"
        assert create_headline_variables["input"]["collaborationEnabled"] is True

    def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"CreateHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        ops.create(349524, "SDK v2 test headline")

        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["assignee"] == 1305290

    def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            ops.update(987654)

    def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field to `EditHeadline`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = ops.update(987654, title="New title")

        assert result.id == 987654
        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"headlineId": 987654, "title": "New title"}}

    def test_update_user_id_sends_assignee(self) -> None:
        """`update(user_id=...)` sends the `assignee` field, not `assigneeId`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        ops.update(987654, user_id=42)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"headlineId": 987654, "assignee": 42}

    def test_update_raises_graphql_error_on_top_level_error(self) -> None:
        """`update()` raises `GraphQLError` when the response carries `errors`.

        Unlike `EditIssue`, `EditHeadline` returns a plain `IdModel { id }`
        with no `success`/`message` fields, so failures surface only through
        the top-level GraphQL `errors` array.
        """
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "headline not found"}]}
        )

        with pytest.raises(GraphQLError, match="headline not found"):
            ops.update(987654, title="New title")

    def test_archive(self) -> None:
        """`archive()` sends `archived: true`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditHeadline": {"id": 987654}}}),
            _response({"data": {"headline": {**HEADLINE_NODE, "archived": True}}}),
        ]

        result = ops.archive(987654)

        assert result.archived is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"headlineId": 987654, "archived": True}

    def test_restore(self) -> None:
        """`restore()` sends `archived: false`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        ops.restore(987654)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"headlineId": 987654, "archived": False}

    def test_update_with_notes_calls_create_note_first(self) -> None:
        """`update(notes=...)` calls `CreateNote` before `EditHeadline`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-77"}}}),
            _response({"data": {"EditHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = ops.update(987654, notes="Updated notes")

        assert result.id == 987654
        assert client.post.call_count == 3
        note_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert note_variables == {"text": "Updated notes"}
        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "headlineId": 987654,
            "notesId": "pad-77",
            "collaborationEnabled": True,
        }

    def test_update_all_fields_together(self) -> None:
        """`update()` with every field set sends all of them at once."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-1"}}}),
            _response({"data": {"EditHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        ops.update(987654, title="New title", user_id=42, notes="notes")

        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "headlineId": 987654,
            "title": "New title",
            "assignee": 42,
            "notesId": "pad-1",
            "collaborationEnabled": True,
        }

    def test_create_notes_failure_skips_create_headline(self) -> None:
        """If `CreateNote` fails, `create()` raises before calling `CreateHeadline`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "CreateNote": {
                        "success": False,
                        "message": "pad service unavailable",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="pad service unavailable"):
            ops.create(349524, "SDK v2 test headline", user_id=1305290, notes="hello")

        assert client.post.call_count == 1

    def test_create_with_notes_sends_exact_input(self) -> None:
        """`create(notes=...)` sends the exact `CreateHeadline` input shape."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-99"}}}),
            _response({"data": {"CreateHeadline": {"id": 987654}}}),
            _response({"data": {"headline": HEADLINE_NODE}}),
        ]

        ops.create(349524, "SDK v2 test headline", user_id=1305290, notes="hello")

        note_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert note_variables == {"text": "hello"}
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables == {
            "input": {
                "title": "SDK v2 test headline",
                "assignee": 1305290,
                "meetings": [349524],
                "notesId": "pad-99",
                "collaborationEnabled": True,
            }
        }

    def test_details_with_null_meeting(self) -> None:
        """A headline with a `null` `meeting` produces `meeting=None`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        node = {**HEADLINE_NODE, "meeting": None}
        client.post.return_value = _response({"data": {"headline": node}})

        result = ops.details(987654)

        assert result.meeting is None

    def test_details_transforms_timestamps_to_utc_aware_datetimes(self) -> None:
        """`created_date`/`archived_date` become timezone-aware UTC datetimes."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        node = {**HEADLINE_NODE, "archived": True, "archivedTimestamp": 1790300000}
        client.post.return_value = _response({"data": {"headline": node}})

        result = ops.details(987654)

        assert result.created_date == datetime.fromtimestamp(1790275733, tz=UTC)
        assert result.created_date.tzinfo is UTC
        assert result.archived_date == datetime.fromtimestamp(1790300000, tz=UTC)
        assert result.archived_date is not None and result.archived_date.tzinfo is UTC

    def test_details_archived_date_is_none_when_not_archived(self) -> None:
        """`archived_date` is `None` when `archivedTimestamp` is `null`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"headline": HEADLINE_NODE}})

        result = ops.details(987654)

        assert result.archived_date is None

    def test_details_notes_from_local_html_when_not_collaborative(self) -> None:
        """Non-collaborative headlines take notes from `localHtml`, not `notesText`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        node = {
            **HEADLINE_NODE,
            "collaborationEnabled": False,
            "notesText": "",
            "localHtml": "<p>hello &amp; world</p>",
        }
        client.post.return_value = _response({"data": {"headline": node}})

        result = ops.details(987654)

        assert result.notes == "hello & world"

    def test_details_notes_none_when_empty(self) -> None:
        """A headline with no description at all yields `notes=None`."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        node = {
            **HEADLINE_NODE,
            "collaborationEnabled": False,
            "notesText": "",
            "localHtml": None,
        }
        client.post.return_value = _response({"data": {"headline": node}})

        result = ops.details(987654)

        assert result.notes is None

    def test_details_raises_graphql_error_on_http_400(self) -> None:
        """`details()` raises `GraphQLError` for an HTTP 400 validation error."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "headline id required"}]}, status_code=400
        )

        with pytest.raises(GraphQLError, match="headline id required") as exc_info:
            ops.details(987654)

        assert exc_info.value.status_code == 400

    def test_list_raises_graphql_error_on_200_with_errors(self) -> None:
        """`list()` raises `GraphQLError` for an execution error (200 + `errors`)."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "boom"}], "data": {"meeting": None}}
        )

        with pytest.raises(GraphQLError, match="boom"):
            ops.list(meeting_id=349524)

    def test_list_by_meeting_returns_empty_when_meeting_is_null(self) -> None:
        """A `null` `meeting` (no view permission) yields an empty list, not a crash."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"meeting": None}})

        result = ops.list(meeting_id=349524)

        assert result == []

    def test_list_by_user_missing_headlines_key_returns_empty_list(self) -> None:
        """A response with no `headlines` key at all yields an empty list."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {}})

        result = ops.list(user_id=1305290)

        assert result == []

    def test_list_by_meeting_include_archived_when_archived_connection_is_null(
        self,
    ) -> None:
        """`include_archived=True` handles a `null` `archivedHeadlines` connection."""
        client = Mock()
        ops = HeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"meeting": {"headlines": {"nodes": [HEADLINE_NODE]}}}}),
            _response({"data": {"meeting": {"archivedHeadlines": None}}}),
        ]

        result = ops.list(meeting_id=349524, include_archived=True)

        assert len(result) == 1
        assert result[0].id == 987654


class TestHeadlineOperationsAsync:
    """Tests for the async `AsyncHeadlineOperations`."""

    @pytest.mark.asyncio
    async def test_details(self) -> None:
        """`details()` returns a transformed `Headline`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"headline": HEADLINE_NODE}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.details(987654)

        assert result.id == 987654
        assert result.notes == "some notes"

    @pytest.mark.asyncio
    async def test_list_both_meeting_and_user_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="not both"):
            await ops.list(meeting_id=349524, user_id=1305290)

    @pytest.mark.asyncio
    async def test_list_by_user_filters_archived_client_side(self) -> None:
        """`list(user_id=...)` drops archived headlines client-side by default."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        archived_node = {**HEADLINE_NODE, "id": 999, "archived": True}
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "data": {"headlines": {"nodes": [HEADLINE_NODE, archived_node]}}
        }
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.list(user_id=1305290)

        assert len(result) == 1
        assert result[0].id == 987654

    @pytest.mark.asyncio
    async def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            await ops.update(987654)

    @pytest.mark.asyncio
    async def test_create_with_notes(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateHeadline`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)

        note_response = MagicMock()
        note_response.status_code = 200
        note_response.json.return_value = {
            "data": {"CreateNote": {"success": True, "data": "pad-99"}}
        }
        note_response.raise_for_status = MagicMock()

        create_response = MagicMock()
        create_response.status_code = 200
        create_response.json.return_value = {"data": {"CreateHeadline": {"id": 987654}}}
        create_response.raise_for_status = MagicMock()

        details_response = MagicMock()
        details_response.status_code = 200
        details_response.json.return_value = {"data": {"headline": HEADLINE_NODE}}
        details_response.raise_for_status = MagicMock()

        client.post.side_effect = [note_response, create_response, details_response]

        result = await ops.create(
            349524, "SDK v2 test headline", user_id=1305290, notes="hello"
        )

        assert result.id == 987654
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["notesId"] == "pad-99"

    @pytest.mark.asyncio
    async def test_archive_and_restore(self) -> None:
        """Each single-field mutation sends only its own field."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)

        def edit_ok() -> MagicMock:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": {"EditHeadline": {"id": 987654}}}
            response.raise_for_status = MagicMock()
            return response

        def details() -> MagicMock:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": {"headline": HEADLINE_NODE}}
            response.raise_for_status = MagicMock()
            return response

        client.post.side_effect = [edit_ok(), details(), edit_ok(), details()]

        await ops.archive(987654)
        await ops.restore(987654)

        assert client.post.call_count == 4

    @pytest.mark.asyncio
    async def test_details_with_null_assignee(self) -> None:
        """A headline with a `null` `assignee` produces `owner=None`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        node = {**HEADLINE_NODE, "assignee": None}
        client.post.return_value = _async_response({"data": {"headline": node}})

        result = await ops.details(987654)

        assert result.owner is None

    @pytest.mark.asyncio
    async def test_details_transforms_timestamps_to_utc_aware_datetimes(self) -> None:
        """`created_date`/`archived_date` become timezone-aware UTC datetimes."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        node = {**HEADLINE_NODE, "archived": True, "archivedTimestamp": 1790300000}
        client.post.return_value = _async_response({"data": {"headline": node}})

        result = await ops.details(987654)

        assert result.created_date == datetime.fromtimestamp(1790275733, tz=UTC)
        assert result.created_date.tzinfo is UTC
        assert result.archived_date == datetime.fromtimestamp(1790300000, tz=UTC)

    @pytest.mark.asyncio
    async def test_details_raises_graphql_error_on_http_400(self) -> None:
        """`details()` raises `GraphQLError` for an HTTP 400 validation error."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"errors": [{"message": "headline id required"}]}, status_code=400
        )

        with pytest.raises(GraphQLError, match="headline id required") as exc_info:
            await ops.details(987654)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_list_by_meeting_open_only(self) -> None:
        """`list(meeting_id=...)` queries `meeting.headlines` (open only) by default."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"meeting": {"headlines": {"nodes": [HEADLINE_NODE]}}}}
        )

        result = await ops.list(meeting_id=349524)

        assert len(result) == 1
        assert client.post.call_count == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"meetingId": 349524}

    @pytest.mark.asyncio
    async def test_list_by_meeting_include_archived_merges(self) -> None:
        """`list(meeting_id=..., include_archived=True)` merges `archivedHeadlines`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        archived_node = {**HEADLINE_NODE, "id": 999, "archived": True}
        client.post.side_effect = [
            _async_response(
                {"data": {"meeting": {"headlines": {"nodes": [HEADLINE_NODE]}}}}
            ),
            _async_response(
                {"data": {"meeting": {"archivedHeadlines": {"nodes": [archived_node]}}}}
            ),
        ]

        result = await ops.list(meeting_id=349524, include_archived=True)

        assert client.post.call_count == 2
        assert {headline.id for headline in result} == {987654, 999}
        second_query = client.post.call_args_list[1].kwargs["json"]["query"]
        assert "archivedHeadlines" in second_query

    @pytest.mark.asyncio
    async def test_list_by_meeting_returns_empty_when_meeting_is_null(self) -> None:
        """A `null` `meeting` (no view permission) yields an empty list, not a crash."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"meeting": None}})

        result = await ops.list(meeting_id=349524)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_by_user_include_archived_keeps_all(self) -> None:
        """`list(user_id=..., include_archived=True)` keeps archived headlines."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        archived_node = {**HEADLINE_NODE, "id": 999, "archived": True}
        client.post.return_value = _async_response(
            {"data": {"headlines": {"nodes": [HEADLINE_NODE, archived_node]}}}
        )

        result = await ops.list(user_id=1305290, include_archived=True)

        assert {headline.id for headline in result} == {987654, 999}

    @pytest.mark.asyncio
    async def test_list_defaults_to_current_user(self) -> None:
        """`list()` with neither id given fetches headlines for the current user."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"headlines": {"nodes": [HEADLINE_NODE]}}}),
        ]

        result = await ops.list()

        assert len(result) == 1
        variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert variables == {"userId": 1305290}

    @pytest.mark.asyncio
    async def test_create_without_notes(self) -> None:
        """`create()` without notes skips `CreateNote` and reads back details."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateHeadline": {"id": 987654}}}),
            _async_response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = await ops.create(349524, "SDK v2 test headline", user_id=1305290)

        assert result.id == 987654
        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables == {
            "input": {
                "title": "SDK v2 test headline",
                "assignee": 1305290,
                "meetings": [349524],
            }
        }

    @pytest.mark.asyncio
    async def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"CreateHeadline": {"id": 987654}}}),
            _async_response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = await ops.create(349524, "SDK v2 test headline")

        assert result.id == 987654
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["assignee"] == 1305290

    @pytest.mark.asyncio
    async def test_create_notes_failure_skips_create_headline(self) -> None:
        """If `CreateNote` fails, `create()` raises before calling `CreateHeadline`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {
                "data": {
                    "CreateNote": {
                        "success": False,
                        "message": "pad service unavailable",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="pad service unavailable"):
            await ops.create(
                349524, "SDK v2 test headline", user_id=1305290, notes="hello"
            )

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field to `EditHeadline`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditHeadline": {"id": 987654}}}),
            _async_response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = await ops.update(987654, title="New title")

        assert result.id == 987654
        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"headlineId": 987654, "title": "New title"}}

    @pytest.mark.asyncio
    async def test_update_user_id_sends_assignee(self) -> None:
        """`update(user_id=...)` sends the `assignee` field, not `assigneeId`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditHeadline": {"id": 987654}}}),
            _async_response({"data": {"headline": HEADLINE_NODE}}),
        ]

        await ops.update(987654, user_id=42)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"headlineId": 987654, "assignee": 42}

    @pytest.mark.asyncio
    async def test_update_with_notes_calls_create_note_first(self) -> None:
        """`update(notes=...)` calls `CreateNote` before `EditHeadline`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-77"}}}
            ),
            _async_response({"data": {"EditHeadline": {"id": 987654}}}),
            _async_response({"data": {"headline": HEADLINE_NODE}}),
        ]

        result = await ops.update(987654, notes="Updated notes")

        assert result.id == 987654
        assert client.post.call_count == 3
        note_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert note_variables == {"text": "Updated notes"}
        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "headlineId": 987654,
            "notesId": "pad-77",
            "collaborationEnabled": True,
        }

    @pytest.mark.asyncio
    async def test_update_raises_graphql_error_on_top_level_error(self) -> None:
        """`update()` raises `GraphQLError` when the response carries `errors`."""
        client = AsyncMock()
        ops = AsyncHeadlineOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"errors": [{"message": "headline not found"}]}
        )

        with pytest.raises(GraphQLError, match="headline not found"):
            await ops.update(987654, title="New title")
