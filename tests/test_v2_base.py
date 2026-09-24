"""Tests for the v2 (GraphQL) transport and shared helpers."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import httpx
import pytest

from bloomy.exceptions import GraphQLError
from bloomy.utils.abstract_operations import AbstractOperations
from bloomy.v2.base import (
    AsyncGraphQLOperations,
    GraphQLOperations,
    UserIdCache,
    compact,
    default_due_date,
    dig_nodes,
    extract_notes,
    merge_nodes,
    now_timestamp,
    prepare_note_text,
    to_timestamp,
    to_utc_datetime,
)

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"


def _response(
    json_data: object, status_code: int = 200, raise_error: Exception | None = None
) -> Mock:
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    if raise_error is not None:
        response.raise_for_status.side_effect = raise_error
    else:
        response.raise_for_status = Mock()
    return response


class TestParseResponse:
    """Tests for `_parse_response` (shared by `_execute`)."""

    def test_returns_data_on_success(self) -> None:
        """A clean 200 with `data` and no `errors` returns `data`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"user": {"id": 1}}})

        result = ops._execute("query {}")

        assert result == {"user": {"id": 1}}

    def test_missing_data_returns_empty_dict(self) -> None:
        """A response with no `data` key returns an empty dict."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({})

        assert ops._execute("query {}") == {}

    def test_http_400_with_errors_raises_graphql_error(self) -> None:
        """A validation error (HTTP 400 + `errors`) raises `GraphQLError`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "field does not exist"}]}, status_code=400
        )

        with pytest.raises(GraphQLError) as exc_info:
            ops._execute("query {}")

        assert exc_info.value.status_code == 400
        assert exc_info.value.errors == [{"message": "field does not exist"}]
        assert "field does not exist" in str(exc_info.value)

    def test_execution_error_200_with_errors_raises_graphql_error(self) -> None:
        """An execution error (HTTP 200 + `errors` alongside `data`) still raises."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "boom"}], "data": {"issue": None}}
        )

        with pytest.raises(GraphQLError) as exc_info:
            ops._execute("query {}")

        assert exc_info.value.status_code == 200
        assert exc_info.value.errors == [{"message": "boom"}]

    def test_non_json_failure_falls_back_to_raise_for_status(self) -> None:
        """A non-JSON failure response (e.g. plain-text 500) raises via httpx."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        response = Mock(spec=httpx.Response)
        response.status_code = 500
        response.json.side_effect = ValueError("not json")
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=Mock(), response=response
        )
        client.post.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            ops._execute("query {}")

    def test_non_json_success_reraises_decode_error(self) -> None:
        """A non-JSON body with a 2xx status re-raises the JSON decode error."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.json.side_effect = ValueError("not json")
        response.raise_for_status = Mock()
        client.post.return_value = response

        with pytest.raises(ValueError, match="not json"):
            ops._execute("query {}")

    def test_json_without_errors_still_calls_raise_for_status(self) -> None:
        """A JSON body without `errors` still surfaces a non-2xx via httpx.

        This is what makes an expired-token 401 (or any JSON error body that
        does not carry an `errors` array) raise a clear error instead of
        failing deep inside `data` access.
        """
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        response = _response(
            {"message": "Unauthorized"},
            status_code=401,
            raise_error=httpx.HTTPStatusError("401", request=Mock(), response=Mock()),
        )
        client.post.return_value = response

        with pytest.raises(httpx.HTTPStatusError):
            ops._execute("query {}")


class TestMergeNodes:
    """Tests for `merge_nodes`."""

    def test_dedupes_by_id_keeping_first_occurrence(self) -> None:
        """A node appearing in multiple lists is kept only once, first wins."""
        first = {"id": 1, "dateCreated": 100, "title": "first"}
        duplicate = {"id": 1, "dateCreated": 100, "title": "duplicate"}

        result = merge_nodes([first], [duplicate])

        assert result == [first]

    def test_sorts_by_date_created_then_id(self) -> None:
        """Merged nodes are sorted by `(dateCreated, id)`, not input order."""
        newer = {"id": 2, "dateCreated": 200}
        older = {"id": 1, "dateCreated": 100}
        tie_a = {"id": 10, "dateCreated": 150}
        tie_b = {"id": 5, "dateCreated": 150}

        result = merge_nodes([newer, older], [tie_a, tie_b])

        assert [node["id"] for node in result] == [1, 5, 10, 2]

    def test_empty_lists_return_empty(self) -> None:
        """Merging only empty lists returns an empty list."""
        assert merge_nodes([], []) == []


class TestDigNodes:
    """Tests for `dig_nodes`."""

    def test_reads_nested_connection_nodes(self) -> None:
        """Nested keys are walked down to the connection's `nodes`."""
        data = {"meeting": {"issues": {"nodes": [{"id": 1}]}}}

        assert dig_nodes(data, "meeting", "issues") == [{"id": 1}]

    @pytest.mark.parametrize(
        "data",
        [None, {}, {"meeting": None}, {"meeting": {"issues": None}}],
    )
    def test_missing_levels_return_empty(self, data: dict[str, Any] | None) -> None:
        """Any missing or `null` level yields an empty list."""
        assert dig_nodes(data, "meeting", "issues") == []


class TestOne:
    """Tests for `_one`."""

    def test_returns_entity_when_present(self) -> None:
        """A present, non-null entity is returned unchanged."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        result = ops._one({"issue": {"id": 1}}, "issue", label="Issue", entity_id=1)

        assert result == {"id": 1}

    def test_raises_when_field_missing(self) -> None:
        """A response with no such key at all raises `GraphQLError`."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="Issue 999 not found"):
            ops._one({}, "issue", label="Issue", entity_id=999)

    def test_raises_when_field_is_null(self) -> None:
        """A `null` entity (unknown or invisible id) raises `GraphQLError`."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="Meeting 999999999 not found"):
            ops._one({"meeting": None}, "meeting", label="Meeting", entity_id=999999999)

    def test_connection_path_returns_first_node(self) -> None:
        """A path ending at a `{nodes}` connection returns its first node."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)
        data = {"goal": {"milestones": {"nodes": [{"id": 5}, {"id": 6}]}}}

        result = ops._one(data, "goal", "milestones", label="Milestone", entity_id=5)

        assert result == {"id": 5}

    def test_list_path_returns_first_item(self) -> None:
        """A path ending at a plain list returns its first item."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)
        data = {"metric": {"scoresNonPaginated": [{"id": 7}]}}

        result = ops._one(
            data, "metric", "scoresNonPaginated", label="Score", entity_id=7
        )

        assert result == {"id": 7}

    @pytest.mark.parametrize(
        "data",
        [
            {"goal": {"milestones": {"nodes": []}}},
            {"goal": None},
            {"goal": {"milestones": []}},
        ],
    )
    def test_empty_or_missing_list_raises(self, data: dict[str, Any]) -> None:
        """An empty connection, or a missing parent, raises `GraphQLError`."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="Milestone 5 not found"):
            ops._one(data, "goal", "milestones", label="Milestone", entity_id=5)


class TestCheckMutationResult:
    """Tests for `_check_mutation_result` (shared by `_mutate`)."""

    def test_success_returns_result(self) -> None:
        """A `success: true` result is returned unchanged."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        result = ops._check_mutation_result({"success": True}, action="do thing")

        assert result == {"success": True}

    def test_success_false_raises_with_message(self) -> None:
        """A `success: false` result raises with the top-level `message`."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="not allowed"):
            ops._check_mutation_result(
                {"success": False, "message": "not allowed", "errorDetails": None},
                action="do thing",
            )

    def test_success_false_falls_back_to_error_details(self) -> None:
        """Without a top-level `message`, `errorDetails` messages are used."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="bad title") as exc_info:
            ops._check_mutation_result(
                {
                    "success": False,
                    "message": None,
                    "errorDetails": [{"message": "bad title"}],
                },
                action="do thing",
            )
        assert exc_info.value.errors == [{"message": "bad title"}]

    def test_success_false_without_messages_uses_action(self) -> None:
        """Without any message, the action name is used."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="do thing failed"):
            ops._check_mutation_result({"success": False}, action="do thing")

    @pytest.mark.parametrize("result", [None, {}])
    def test_missing_result_raises(self, result: dict[str, Any] | None) -> None:
        """A missing (`null`) or empty result raises with the action name."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="do thing failed: no result"):
            ops._check_mutation_result(result, action="do thing")

    def test_nonzero_id_returns_result(self) -> None:
        """An `IdModel` result with a non-zero `id` is returned unchanged."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        result = ops._check_mutation_result({"id": 5265048}, action="create goal")

        assert result == {"id": 5265048}

    def test_zero_id_raises(self) -> None:
        """An `id` of `0` (e.g. a failed `CreateGoal`) raises."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="create goal failed: no id"):
            ops._check_mutation_result({"id": 0}, action="create goal")


class TestMutate:
    """Tests for the sync and async `_mutate`."""

    def test_returns_result_on_success(self) -> None:
        """`_mutate` returns the root field's result on success."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"EditIssue": {"success": True, "message": None}}}
        )

        result = ops._mutate(
            "mutation {}", {"input": {}}, root_field="EditIssue", action="update"
        )

        assert result == {"success": True, "message": None}

    def test_raises_on_failure(self) -> None:
        """`_mutate` raises `GraphQLError` when `success` is false."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "EditIssue": {
                        "success": False,
                        "message": "nope",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="nope"):
            ops._mutate(
                "mutation {}", {"input": {}}, root_field="EditIssue", action="update"
            )

    def test_raises_on_null_create_result(self) -> None:
        """A `null` `Create*` result raises rather than returning `None`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"CreateGoal": None}})

        with pytest.raises(GraphQLError, match="create goal failed"):
            ops._mutate(
                "mutation {}", {}, root_field="CreateGoal", action="create goal"
            )

    @pytest.mark.asyncio
    async def test_async_raises_on_zero_id(self) -> None:
        """The async `_mutate` applies the same checks."""
        client = AsyncMock()
        ops = AsyncGraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"CreateGoal": {"id": 0}}})

        with pytest.raises(GraphQLError, match="create goal failed"):
            await ops._mutate(
                "mutation {}", {}, root_field="CreateGoal", action="create goal"
            )


class TestCreateNote:
    """Tests for `_create_note`."""

    def test_create_note_escapes_and_returns_pad_id(self) -> None:
        """`_create_note` escapes the text and returns the new pad id."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"CreateNote": {"success": True, "data": "pad-123"}}}
        )

        pad_id = ops._create_note("line one\nline two & <b>raw</b>")

        assert pad_id == "pad-123"
        sent_variables = client.post.call_args.kwargs["json"]["variables"]
        assert sent_variables == {
            "text": "line one<br>line two &amp; &lt;b&gt;raw&lt;/b&gt;"
        }

    def test_create_note_raises_on_failure(self) -> None:
        """`_create_note` raises `GraphQLError` when `CreateNote` fails."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "CreateNote": {
                        "success": False,
                        "message": "nope",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError):
            ops._create_note("text")


class TestNotesInput:
    """Tests for the sync and async `_notes_input`."""

    def test_none_returns_empty_without_request(self) -> None:
        """`None` notes add no input fields and create no pad."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        assert ops._notes_input(None) == {}
        client.post.assert_not_called()

    def test_text_creates_pad(self) -> None:
        """Notes text creates a pad and enables collaboration mode."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"CreateNote": {"success": True, "data": "pad-1"}}}
        )

        assert ops._notes_input("hello") == {
            "notesId": "pad-1",
            "collaborationEnabled": True,
        }

    @pytest.mark.asyncio
    async def test_async_text_creates_pad(self) -> None:
        """The async variant creates a pad the same way."""
        client = AsyncMock()
        ops = AsyncGraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"CreateNote": {"success": True, "data": "pad-2"}}}
        )

        assert await ops._notes_input("hello") == {
            "notesId": "pad-2",
            "collaborationEnabled": True,
        }
        assert await ops._notes_input(None) == {}
        client.post.assert_called_once()


class TestTimestampHelpers:
    """Tests for the module-level timestamp and due-date helpers."""

    def test_naive_datetime_treated_as_utc(self) -> None:
        """A naive datetime is treated as UTC."""
        naive = datetime(2024, 1, 1, 0, 0, 0)
        aware = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert to_utc_datetime(naive) == aware
        assert to_timestamp(naive) == aware.timestamp()

    def test_aware_datetime_preserved(self) -> None:
        """A timezone-aware datetime converts directly."""
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        assert to_utc_datetime(aware) is aware
        assert to_timestamp(aware) == aware.timestamp()

    def test_date_becomes_midnight_utc(self) -> None:
        """A `date` becomes 00:00 UTC of that day."""
        expected = datetime(2024, 1, 1, tzinfo=UTC)

        assert to_utc_datetime(date(2024, 1, 1)) == expected
        assert to_timestamp(date(2024, 1, 1)) == expected.timestamp()

    def test_numbers(self) -> None:
        """Numbers pass through `to_timestamp` and convert in `to_utc_datetime`."""
        assert to_timestamp(1700000000) == 1700000000.0
        assert to_timestamp(1700000000.5) == 1700000000.5
        assert to_utc_datetime(1700000000) == datetime(
            2023, 11, 14, 22, 13, 20, tzinfo=UTC
        )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("2026-09-21", datetime(2026, 9, 21, tzinfo=UTC)),
            ("2026-09-21T10:30:00", datetime(2026, 9, 21, 10, 30, tzinfo=UTC)),
            ("2026-09-21T10:30:00+02:00", datetime(2026, 9, 21, 8, 30, tzinfo=UTC)),
        ],
    )
    def test_iso_strings(self, value: str, expected: datetime) -> None:
        """ISO 8601 strings parse like datetimes; no offset means UTC."""
        assert to_utc_datetime(value) == expected
        assert to_timestamp(value) == expected.timestamp()

    def test_invalid_string_raises(self) -> None:
        """A string that is not ISO 8601 raises `ValueError`."""
        with pytest.raises(ValueError):
            to_timestamp("next tuesday")

    def test_now_timestamp_is_close_to_now(self) -> None:
        """`now_timestamp` is close to the current time."""
        assert abs(now_timestamp() - datetime.now(tz=UTC).timestamp()) < 5

    def test_default_due_date_counts_from_utc_today(self) -> None:
        """`default_due_date` adds days to today's UTC date."""
        expected = datetime.now(tz=UTC).date() + timedelta(days=7)

        assert default_due_date(7) == expected


class TestCompact:
    """Tests for `compact`."""

    def test_drops_only_none(self) -> None:
        """`None` values are dropped; falsy non-`None` values are kept."""
        assert compact(a=None, b=0, c=False, d="", e="x") == {
            "b": 0,
            "c": False,
            "d": "",
            "e": "x",
        }


class TestNotesHelpers:
    """Tests for `prepare_note_text` and `extract_notes`."""

    def test_prepare_note_text_escapes_and_converts_newlines(self) -> None:
        """Newlines become `<br>`, and HTML-sensitive characters are escaped."""
        assert prepare_note_text("a & b\n<c>") == "a &amp; b<br>&lt;c&gt;"

    def test_extract_notes_collaboration_enabled(self) -> None:
        """When `collaborationEnabled`, use `notesText`, stripping trailing newlines."""
        data = {
            "collaborationEnabled": True,
            "notesText": "hello world\n\n",
            "localHtml": None,
        }

        assert extract_notes(data) == "hello world"

    def test_extract_notes_local_html_fallback(self) -> None:
        """When not `collaborationEnabled`, strip tags and unescape `localHtml`."""
        data = {
            "collaborationEnabled": False,
            "notesText": "",
            "localHtml": "<p>hello &amp; world</p>",
        }

        assert extract_notes(data) == "hello & world"

    def test_extract_notes_empty_returns_none(self) -> None:
        """An empty description returns `None`."""
        data = {"collaborationEnabled": True, "notesText": "", "localHtml": None}

        assert extract_notes(data) is None


class TestSyncUserId:
    """Tests for the sync `user_id` property."""

    def test_fetches_and_caches(self) -> None:
        """`user_id` fetches via `getAuthenticatedUserId` and caches the result."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"getAuthenticatedUserId": {"id": 42}}}
        )

        assert ops.user_id == 42
        assert ops.user_id == 42
        client.post.assert_called_once()

    def test_shared_cache_fetches_once(self) -> None:
        """Operations sharing a `UserIdCache` fetch the user id only once."""
        client = Mock()
        cache = UserIdCache()
        first = GraphQLOperations(client, GRAPHQL_URL, cache)
        second = GraphQLOperations(client, GRAPHQL_URL, cache)
        client.post.return_value = _response(
            {"data": {"getAuthenticatedUserId": {"id": 42}}}
        )

        assert first.user_id == 42
        assert second.user_id == 42
        client.post.assert_called_once()

    def test_is_a_v1_abstract_operations(self) -> None:
        """v2 operations reuse v1's `AbstractOperations` helpers."""
        ops = GraphQLOperations(Mock(), GRAPHQL_URL)

        assert isinstance(ops, AbstractOperations)
        with pytest.raises(ValueError, match="Cannot specify both"):
            ops._validate_mutual_exclusion(1, 2, "meeting_id", "user_id")


class TestAsyncUserId:
    """Tests for the async `user_id`/`get_user_id`."""

    def test_user_id_raises_before_fetch(self) -> None:
        """Accessing `user_id` before `get_user_id()` raises `RuntimeError`."""
        client = AsyncMock()
        ops = AsyncGraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(RuntimeError):
            _ = ops.user_id

    @pytest.mark.asyncio
    async def test_get_user_id_fetches_and_caches(self) -> None:
        """`get_user_id()` fetches via `getAuthenticatedUserId` and caches it."""
        client = AsyncMock()
        ops = AsyncGraphQLOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"getAuthenticatedUserId": {"id": 7}}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        assert await ops.get_user_id() == 7
        assert ops.user_id == 7
        client.post.assert_called_once()

    def test_user_id_setter(self) -> None:
        """The `user_id` setter caches without a fetch."""
        client = AsyncMock()
        ops = AsyncGraphQLOperations(client, GRAPHQL_URL)
        ops.user_id = 99

        assert ops.user_id == 99

    @pytest.mark.asyncio
    async def test_concurrent_lookups_share_one_fetch(self) -> None:
        """Concurrent `get_user_id()` calls on a shared cache fetch only once."""
        client = AsyncMock()
        cache = UserIdCache()
        first = AsyncGraphQLOperations(client, GRAPHQL_URL, cache)
        second = AsyncGraphQLOperations(client, GRAPHQL_URL, cache)

        async def slow_post(*_args: object, **_kwargs: object) -> Mock:
            await asyncio.sleep(0.01)
            return _response({"data": {"getAuthenticatedUserId": {"id": 7}}})

        client.post.side_effect = slow_post

        results = await asyncio.gather(
            first.get_user_id(), second.get_user_id(), first.get_user_id()
        )

        assert results == [7, 7, 7]
        assert second.user_id == 7
        client.post.assert_called_once()
