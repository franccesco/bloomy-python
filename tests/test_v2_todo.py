"""Tests for the v2 (GraphQL) to-do operations."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.models import Todo
from bloomy.v2.operations.todo import AsyncTodoOperations, TodoOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

TODO_NODE = {
    "id": 555001,
    "title": "SDK v2 test to-do",
    "dueDate": 1790275733,
    "completed": False,
    "completedTimestamp": None,
    "archived": False,
    "archivedTimestamp": None,
    "dateCreated": 1789275733,
    "notesId": "pad-1",
    "notesText": "some notes\n",
    "localHtml": None,
    "collaborationEnabled": True,
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


class TestTodoOperationsSync:
    """Tests for the sync `TodoOperations`."""

    def test_details(self) -> None:
        """`details()` returns a transformed `Todo`, including plain-text notes."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"todo": TODO_NODE}})

        result = ops.details(555001)

        assert isinstance(result, Todo)
        assert result.id == 555001
        assert result.owner is not None and result.owner.id == 1305290
        assert result.meeting is not None and result.meeting.id == 349524
        assert result.notes == "some notes"

    def test_details_with_null_assignee(self) -> None:
        """A to-do with a `null` `assignee` produces `owner=None`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        node = {**TODO_NODE, "assignee": None}
        client.post.return_value = _response({"data": {"todo": node}})

        result = ops.details(555001)

        assert result.owner is None

    def test_details_with_null_meeting(self) -> None:
        """A personal to-do (`meeting: null`) produces `meeting=None`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        node = {**TODO_NODE, "meeting": None}
        client.post.return_value = _response({"data": {"todo": node}})

        result = ops.details(555001)

        assert result.meeting is None

    def test_details_datetime_fields_are_utc_aware(self) -> None:
        """Timestamp fields convert into timezone-aware UTC datetimes."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        node = {
            **TODO_NODE,
            "completedTimestamp": 1790300000,
            "archivedTimestamp": 1790400000,
        }
        client.post.return_value = _response({"data": {"todo": node}})

        result = ops.details(555001)

        for value, expected_ts in (
            (result.due_date, 1790275733),
            (result.completed_date, 1790300000),
            (result.archived_date, 1790400000),
            (result.created_date, 1789275733),
        ):
            assert value is not None
            assert value.tzinfo == UTC
            assert value == datetime.fromtimestamp(expected_ts, tz=UTC)

    def test_details_raises_graphql_error_on_http_400(self) -> None:
        """A validation error (HTTP 400 + `errors`) raises `GraphQLError`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "to-do not found"}]}, status_code=400
        )

        with pytest.raises(GraphQLError, match="to-do not found") as exc_info:
            ops.details(555001)
        assert exc_info.value.status_code == 400

    def test_list_both_meeting_and_user_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="not both"):
            ops.list(meeting_id=349524, user_id=1305290)

    def test_list_by_meeting_default_where(self) -> None:
        """`list(meeting_id=...)` excludes completed and archived to-dos by default."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"todos": {"nodes": [TODO_NODE]}}}}
        )

        result = ops.list(meeting_id=349524)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {
            "and": [{"completed": {"eq": False}}, {"archived": {"eq": False}}]
        }

    def test_list_by_meeting_include_completed_and_archived(self) -> None:
        """`include_completed=True, include_archived=True` sends no `where` filter."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"todos": {"nodes": [TODO_NODE]}}}}
        )

        ops.list(meeting_id=349524, include_completed=True, include_archived=True)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] is None

    def test_list_by_meeting_include_completed_only(self) -> None:
        """`include_completed=True` alone still filters out archived to-dos."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"todos": {"nodes": [TODO_NODE]}}}}
        )

        ops.list(meeting_id=349524, include_completed=True)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] == {"and": [{"archived": {"eq": False}}]}

    def test_list_by_meeting_missing_meeting_returns_empty(self) -> None:
        """A `null` `meeting` (e.g. bad id) produces an empty list, not an error."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"meeting": None}})

        result = ops.list(meeting_id=999999)

        assert result == []

    def test_list_raises_graphql_error_on_200_with_errors(self) -> None:
        """An execution error (HTTP 200 + `errors` alongside `data`) still raises."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "boom"}], "data": {"meeting": None}}
        )

        with pytest.raises(GraphQLError, match="boom") as exc_info:
            ops.list(meeting_id=349524)
        assert exc_info.value.status_code == 200

    def test_list_by_user_defaults_to_current_user(self) -> None:
        """`list()` with no arguments defaults to the current user's to-dos."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"todos": {"nodes": [TODO_NODE]}}}),
        ]

        result = ops.list()

        assert len(result) == 1
        list_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert list_variables["userId"] == 1305290

    def test_list_by_user_explicit_id(self) -> None:
        """`list(user_id=...)` queries the root `todos(userId)` connection."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"todos": {"nodes": [TODO_NODE]}}}
        )

        result = ops.list(user_id=1305290)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["userId"] == 1305290
        sent_query = client.post.call_args.kwargs["json"]["query"]
        assert "todos(userId" in sent_query

    def test_list_by_user_include_archived_where_still_sent(self) -> None:
        """`list(user_id=..., include_archived=True)` still builds a `where`.

        The API ignores the `archived` clause server-side for the
        user-scoped connection (see `list()`'s docstring), but the client
        builds `where` the same way regardless of scope: only the
        `completed` clause survives here.
        """
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"todos": {"nodes": [TODO_NODE]}}}
        )

        ops.list(user_id=1305290, include_archived=True)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] == {"and": [{"completed": {"eq": False}}]}

    def test_list_by_user_missing_todos_returns_empty(self) -> None:
        """A missing `todos` connection produces an empty list, not an error."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {}})

        result = ops.list(user_id=1305290)

        assert result == []

    def test_create_without_notes_defaults_due_date_and_user(self) -> None:
        """`create()` without `due_date`/`notes` defaults both, skips `CreateNote`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"CreateTodo": {"id": 555001}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        result = ops.create("SDK v2 test to-do", meeting_id=349524)

        assert result.id == 555001
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        input_ = create_variables["input"]
        assert input_["title"] == "SDK v2 test to-do"
        assert input_["assigneeId"] == 1305290
        assert input_["meetingRecurrenceId"] == 349524
        assert "notesId" not in input_
        assert "collaborationEnabled" not in input_

        due_date = datetime.fromtimestamp(input_["dueDate"], tz=UTC)
        expected_date = (datetime.now(tz=UTC) + timedelta(days=7)).date()
        assert due_date.date() == expected_date
        assert due_date.time() == time(0, 0)

    def test_create_personal_todo_sends_null_meeting_id(self) -> None:
        """`create()` without `meeting_id` sends `meetingRecurrenceId: null`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateTodo": {"id": 555001}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.create("Personal to-do", user_id=1305290)

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables["input"]["meetingRecurrenceId"] is None

    def test_create_with_explicit_due_date(self) -> None:
        """`create(due_date=...)` converts the given date to a unix timestamp."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateTodo": {"id": 555001}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.create(
            "SDK v2 test to-do",
            meeting_id=349524,
            user_id=1305290,
            due_date=date(2026, 10, 1),
        )

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        expected = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
        assert create_variables["input"]["dueDate"] == expected

    def test_create_with_explicit_datetime_due_date_preserves_time(self) -> None:
        """`create(due_date=<aware datetime>)` preserves the time-of-day."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateTodo": {"id": 555001}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]
        due = datetime(2026, 10, 1, 15, 30, tzinfo=UTC)

        ops.create(
            "SDK v2 test to-do", meeting_id=349524, user_id=1305290, due_date=due
        )

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables["input"]["dueDate"] == due.timestamp()

    def test_create_with_notes_calls_create_note_first(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateTodo`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-99"}}}),
            _response({"data": {"CreateTodo": {"id": 555001}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.create(
            "SDK v2 test to-do", meeting_id=349524, user_id=1305290, notes="hello"
        )

        note_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert note_variables == {"text": "hello"}
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["notesId"] == "pad-99"
        assert create_variables["input"]["collaborationEnabled"] is True

    def test_create_raises_graphql_error_when_create_note_fails(self) -> None:
        """`create(notes=...)` propagates a `CreateNote` failure before `CreateTodo`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
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
            ops.create(
                "SDK v2 test to-do", meeting_id=349524, user_id=1305290, notes="hello"
            )
        client.post.assert_called_once()

    def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            ops.update(555001)
        client.post.assert_not_called()

    def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        result = ops.update(555001, title="New title")

        assert result.id == 555001
        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"todoId": 555001, "title": "New title"}}

    def test_update_due_date_only(self) -> None:
        """`update(due_date=...)` sends only the converted due date."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.update(555001, due_date=date(2026, 10, 1))

        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        expected = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
        assert edit_variables == {"input": {"todoId": 555001, "dueDate": expected}}

    def test_update_user_id_only(self) -> None:
        """`update(user_id=...)` sends only the new `assigneeId`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.update(555001, user_id=42)

        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"todoId": 555001, "assigneeId": 42}}

    def test_update_notes_only(self) -> None:
        """`update(notes=...)` calls `CreateNote` then sends `notesId`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-77"}}}),
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.update(555001, notes="updated notes")

        edit_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_variables == {
            "input": {
                "todoId": 555001,
                "notesId": "pad-77",
                "collaborationEnabled": True,
            }
        }

    def test_update_all_fields_together(self) -> None:
        """`update()` with every field set sends all of them at once."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-77"}}}),
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.update(
            555001,
            title="New title",
            due_date=date(2026, 10, 1),
            user_id=42,
            notes="updated notes",
        )

        edit_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        expected_due = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
        assert edit_variables == {
            "input": {
                "todoId": 555001,
                "title": "New title",
                "dueDate": expected_due,
                "assigneeId": 42,
                "notesId": "pad-77",
                "collaborationEnabled": True,
            }
        }

    def test_update_raises_graphql_error_on_failure(self) -> None:
        """`update()` raises `GraphQLError` when `EditTodo` reports failure."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "EditTodo": {
                        "success": False,
                        "message": "nope",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="nope"):
            ops.update(555001, title="New title")

    def test_complete(self) -> None:
        """`complete()` sends a current `completedTimestamp`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": {**TODO_NODE, "completed": True}}}),
        ]

        result = ops.complete(555001)

        assert result.completed is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input["todoId"] == 555001
        assert isinstance(edit_input["completedTimestamp"], float)

    def test_complete_raises_graphql_error_on_failure(self) -> None:
        """`complete()` raises `GraphQLError` when `EditTodo` reports failure."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "EditTodo": {
                        "success": False,
                        "message": None,
                        "errorDetails": [{"message": "to-do is archived"}],
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="to-do is archived") as exc_info:
            ops.complete(555001)
        assert exc_info.value.errors == [{"message": "to-do is archived"}]

    def test_reopen(self) -> None:
        """`reopen()` sends explicit `completedTimestamp: null`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.reopen(555001)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"todoId": 555001, "completedTimestamp": None}

    def test_archive(self) -> None:
        """`archive()` sends a current `archivedTimestamp`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": {**TODO_NODE, "archived": True}}}),
        ]

        result = ops.archive(555001)

        assert result.archived is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input["todoId"] == 555001
        assert isinstance(edit_input["archivedTimestamp"], float)

    def test_restore(self) -> None:
        """`restore()` sends explicit `archivedTimestamp: null`."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _response({"data": {"todo": TODO_NODE}}),
        ]

        ops.restore(555001)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"todoId": 555001, "archivedTimestamp": None}

    def test_restore_raises_graphql_error_on_missing_result(self) -> None:
        """`restore()` raises `GraphQLError` when `EditTodo` is missing entirely."""
        client = Mock()
        ops = TodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {}})

        with pytest.raises(GraphQLError, match="restore todo failed"):
            ops.restore(555001)


class TestTodoOperationsAsync:
    """Tests for the async `AsyncTodoOperations`."""

    @pytest.mark.asyncio
    async def test_details(self) -> None:
        """`details()` returns a transformed `Todo`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"todo": TODO_NODE}})

        result = await ops.details(555001)

        assert result.id == 555001
        assert result.owner is not None and result.owner.id == 1305290
        assert result.meeting is not None and result.meeting.id == 349524
        assert result.notes == "some notes"

    @pytest.mark.asyncio
    async def test_details_with_null_assignee(self) -> None:
        """A to-do with a `null` `assignee` produces `owner=None`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        node = {**TODO_NODE, "assignee": None}
        client.post.return_value = _async_response({"data": {"todo": node}})

        result = await ops.details(555001)

        assert result.owner is None

    @pytest.mark.asyncio
    async def test_details_with_null_meeting(self) -> None:
        """A personal to-do (`meeting: null`) produces `meeting=None`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        node = {**TODO_NODE, "meeting": None}
        client.post.return_value = _async_response({"data": {"todo": node}})

        result = await ops.details(555001)

        assert result.meeting is None

    @pytest.mark.asyncio
    async def test_details_datetime_fields_are_utc_aware(self) -> None:
        """Timestamp fields convert into timezone-aware UTC datetimes."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        node = {
            **TODO_NODE,
            "completedTimestamp": 1790300000,
            "archivedTimestamp": 1790400000,
        }
        client.post.return_value = _async_response({"data": {"todo": node}})

        result = await ops.details(555001)

        for value, expected_ts in (
            (result.due_date, 1790275733),
            (result.completed_date, 1790300000),
            (result.archived_date, 1790400000),
            (result.created_date, 1789275733),
        ):
            assert value is not None
            assert value.tzinfo == UTC
            assert value == datetime.fromtimestamp(expected_ts, tz=UTC)

    @pytest.mark.asyncio
    async def test_details_raises_graphql_error_on_http_400(self) -> None:
        """A validation error (HTTP 400 + `errors`) raises `GraphQLError`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"errors": [{"message": "to-do not found"}]}, status_code=400
        )

        with pytest.raises(GraphQLError, match="to-do not found") as exc_info:
            await ops.details(555001)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_list_both_meeting_and_user_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="not both"):
            await ops.list(meeting_id=349524, user_id=1305290)
        client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_by_meeting_default_where(self) -> None:
        """`list(meeting_id=...)` excludes completed and archived to-dos by default."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"meeting": {"todos": {"nodes": [TODO_NODE]}}}}
        )

        result = await ops.list(meeting_id=349524)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {
            "and": [{"completed": {"eq": False}}, {"archived": {"eq": False}}]
        }

    @pytest.mark.asyncio
    async def test_list_by_meeting_include_completed_and_archived(self) -> None:
        """`include_completed=True, include_archived=True` sends no `where` filter."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"meeting": {"todos": {"nodes": [TODO_NODE]}}}}
        )

        await ops.list(meeting_id=349524, include_completed=True, include_archived=True)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] is None

    @pytest.mark.asyncio
    async def test_list_raises_graphql_error_on_200_with_errors(self) -> None:
        """An execution error (HTTP 200 + `errors` alongside `data`) still raises."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"errors": [{"message": "boom"}], "data": {"meeting": None}}
        )

        with pytest.raises(GraphQLError, match="boom") as exc_info:
            await ops.list(meeting_id=349524)
        assert exc_info.value.status_code == 200

    @pytest.mark.asyncio
    async def test_list_by_user_defaults_to_current_user(self) -> None:
        """`list()` with no arguments defaults to the current user's to-dos."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"todos": {"nodes": [TODO_NODE]}}}),
        ]

        result = await ops.list()

        assert len(result) == 1
        list_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert list_variables["userId"] == 1305290

    @pytest.mark.asyncio
    async def test_list_by_user_explicit_id(self) -> None:
        """`list(user_id=...)` queries the root `todos(userId)` connection."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"todos": {"nodes": [TODO_NODE]}}}
        )

        result = await ops.list(user_id=1305290)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["userId"] == 1305290
        sent_query = client.post.call_args.kwargs["json"]["query"]
        assert "todos(userId" in sent_query

    @pytest.mark.asyncio
    async def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            await ops.update(555001)
        client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_without_notes_defaults_due_date_and_user(self) -> None:
        """`create()` without `due_date`/`notes` defaults both, skips `CreateNote`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"CreateTodo": {"id": 555001}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        result = await ops.create("SDK v2 test to-do", meeting_id=349524)

        assert result.id == 555001
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        input_ = create_variables["input"]
        assert input_["title"] == "SDK v2 test to-do"
        assert input_["assigneeId"] == 1305290
        assert input_["meetingRecurrenceId"] == 349524
        assert "notesId" not in input_

        due_date = datetime.fromtimestamp(input_["dueDate"], tz=UTC)
        expected_date = (datetime.now(tz=UTC) + timedelta(days=7)).date()
        assert due_date.date() == expected_date
        assert due_date.time() == time(0, 0)

    @pytest.mark.asyncio
    async def test_create_personal_todo_sends_null_meeting_id(self) -> None:
        """`create()` without `meeting_id` sends `meetingRecurrenceId: null`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateTodo": {"id": 555001}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        await ops.create("Personal to-do", user_id=1305290)

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables["input"]["meetingRecurrenceId"] is None

    @pytest.mark.asyncio
    async def test_create_with_explicit_due_date(self) -> None:
        """`create(due_date=...)` converts the given date to a unix timestamp."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateTodo": {"id": 555001}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        await ops.create(
            "SDK v2 test to-do",
            meeting_id=349524,
            user_id=1305290,
            due_date=date(2026, 10, 1),
        )

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        expected = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
        assert create_variables["input"]["dueDate"] == expected

    @pytest.mark.asyncio
    async def test_create_with_notes(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateTodo`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-99"}}}
            ),
            _async_response({"data": {"CreateTodo": {"id": 555001}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        result = await ops.create(
            "SDK v2 test to-do", meeting_id=349524, user_id=1305290, notes="hello"
        )

        assert result.id == 555001
        note_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert note_variables == {"text": "hello"}
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["notesId"] == "pad-99"
        assert create_variables["input"]["collaborationEnabled"] is True

    @pytest.mark.asyncio
    async def test_create_raises_graphql_error_when_create_note_fails(self) -> None:
        """`create(notes=...)` propagates a `CreateNote` failure."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
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
                "SDK v2 test to-do", meeting_id=349524, user_id=1305290, notes="hello"
            )
        client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        result = await ops.update(555001, title="New title")

        assert result.id == 555001
        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"todoId": 555001, "title": "New title"}}

    @pytest.mark.asyncio
    async def test_update_due_date_and_user_id(self) -> None:
        """`update(due_date=..., user_id=...)` sends both converted fields."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        await ops.update(555001, due_date=date(2026, 10, 1), user_id=42)

        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        expected = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
        assert edit_variables == {
            "input": {"todoId": 555001, "dueDate": expected, "assigneeId": 42}
        }

    @pytest.mark.asyncio
    async def test_update_notes_only(self) -> None:
        """`update(notes=...)` calls `CreateNote` then sends `notesId`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-77"}}}
            ),
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        await ops.update(555001, notes="updated notes")

        edit_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_variables == {
            "input": {
                "todoId": 555001,
                "notesId": "pad-77",
                "collaborationEnabled": True,
            }
        }

    @pytest.mark.asyncio
    async def test_update_raises_graphql_error_on_failure(self) -> None:
        """`update()` raises `GraphQLError` when `EditTodo` reports failure."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {
                "data": {
                    "EditTodo": {
                        "success": False,
                        "message": "nope",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="nope"):
            await ops.update(555001, title="New title")

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        """`complete()` sends a current `completedTimestamp`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": {**TODO_NODE, "completed": True}}}),
        ]

        result = await ops.complete(555001)

        assert result.completed is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input["todoId"] == 555001
        assert isinstance(edit_input["completedTimestamp"], float)

    @pytest.mark.asyncio
    async def test_reopen(self) -> None:
        """`reopen()` sends explicit `completedTimestamp: null`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        await ops.reopen(555001)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"todoId": 555001, "completedTimestamp": None}

    @pytest.mark.asyncio
    async def test_archive(self) -> None:
        """`archive()` sends a current `archivedTimestamp`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": {**TODO_NODE, "archived": True}}}),
        ]

        result = await ops.archive(555001)

        assert result.archived is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input["todoId"] == 555001
        assert isinstance(edit_input["archivedTimestamp"], float)

    @pytest.mark.asyncio
    async def test_restore(self) -> None:
        """`restore()` sends explicit `archivedTimestamp: null`."""
        client = AsyncMock()
        ops = AsyncTodoOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditTodo": {"success": True, "message": None}}}),
            _async_response({"data": {"todo": TODO_NODE}}),
        ]

        await ops.restore(555001)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"todoId": 555001, "archivedTimestamp": None}
