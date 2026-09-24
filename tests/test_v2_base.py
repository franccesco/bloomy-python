"""Tests for the v2 (GraphQL) transport and shared helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import httpx
import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.base import (
    AsyncGraphQLOperations,
    GraphQLOperations,
    extract_notes,
    merge_nodes,
    prepare_note_text,
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

    def test_custom_date_field(self) -> None:
        """A custom `date_field` is used for sorting instead of `dateCreated`."""
        a = {"id": 1, "timestamp": 200}
        b = {"id": 2, "timestamp": 100}

        result = merge_nodes([a, b], date_field="timestamp")

        assert [node["id"] for node in result] == [2, 1]


class TestRequireEntity:
    """Tests for `_require_entity`."""

    def test_returns_entity_when_present(self) -> None:
        """A present, non-null entity is returned unchanged."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        result = ops._require_entity({"issue": {"id": 1}}, "issue", 1, "Issue")

        assert result == {"id": 1}

    def test_raises_when_field_missing(self) -> None:
        """A response with no `field` key at all raises `GraphQLError`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="Issue 999 not found"):
            ops._require_entity({}, "issue", 999, "Issue")

    def test_raises_when_field_is_null(self) -> None:
        """A `null` entity (unknown or invisible id) raises `GraphQLError`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="Meeting 999999999 not found"):
            ops._require_entity({"meeting": None}, "meeting", 999999999, "Meeting")


class TestRequireCreatedId:
    """Tests for `_require_created_id`."""

    def test_returns_id_when_present(self) -> None:
        """A non-zero `id` is returned as an `int`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        assert ops._require_created_id({"id": 5265048}, label="goal") == 5265048

    def test_raises_when_result_is_none(self) -> None:
        """A `None` mutation result (e.g. a `null` `CreateGoal`) raises."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="create goal failed"):
            ops._require_created_id(None, label="goal")

    def test_raises_when_id_is_zero(self) -> None:
        """An `id` of `0` (e.g. a failed `CreateGoal` returning `IdModel(0)`) raises."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="create goal failed"):
            ops._require_created_id({"id": 0}, label="goal")


class TestCheckMutationResult:
    """Tests for `_check_mutation_result` (shared by `_run_mutation`)."""

    def test_success_does_not_raise(self) -> None:
        """A `success: true` result passes silently."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        ops._check_mutation_result({"success": True}, action="do thing")

    def test_success_false_raises_with_message(self) -> None:
        """A `success: false` result raises with the top-level `message`."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="not allowed"):
            ops._check_mutation_result(
                {"success": False, "message": "not allowed", "errorDetails": None},
                action="do thing",
            )

    def test_success_false_falls_back_to_error_details(self) -> None:
        """Without a top-level `message`, `errorDetails` messages are used."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

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

    def test_missing_result_raises(self) -> None:
        """A missing mutation result (`None`) raises with the action name."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        with pytest.raises(GraphQLError, match="do thing failed"):
            ops._check_mutation_result(None, action="do thing")


class TestRunMutation:
    """Tests for `_run_mutation`."""

    def test_run_mutation_returns_result_on_success(self) -> None:
        """`_run_mutation` returns the root field's result on success."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"EditIssue": {"success": True, "message": None}}}
        )

        result = ops._run_mutation(
            "mutation {}", {"input": {}}, root_field="EditIssue", action="update"
        )

        assert result == {"success": True, "message": None}

    def test_run_mutation_raises_on_failure(self) -> None:
        """`_run_mutation` raises `GraphQLError` when `success` is false."""
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
            ops._run_mutation(
                "mutation {}", {"input": {}}, root_field="EditIssue", action="update"
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


class TestTimestampHelpers:
    """Tests for `_to_timestamp` and `_now_timestamp`."""

    def test_naive_datetime_treated_as_utc(self) -> None:
        """A naive datetime is treated as UTC."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        naive = datetime(2024, 1, 1, 0, 0, 0)
        aware = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert ops._to_timestamp(naive) == aware.timestamp()

    def test_aware_datetime_preserved(self) -> None:
        """A timezone-aware datetime converts directly."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        assert ops._to_timestamp(aware) == aware.timestamp()

    def test_date_becomes_midnight_utc(self) -> None:
        """A `date` becomes 00:00 UTC of that day."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)
        day = date(2024, 1, 1)
        expected = datetime(2024, 1, 1, tzinfo=UTC).timestamp()

        assert ops._to_timestamp(day) == expected

    def test_numbers_pass_through_as_float(self) -> None:
        """A float/int is returned as-is (as a float)."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        assert ops._to_timestamp(1700000000) == 1700000000.0
        assert ops._to_timestamp(1700000000.5) == 1700000000.5

    def test_now_timestamp_is_close_to_now(self) -> None:
        """`_now_timestamp` is close to the current time."""
        client = Mock()
        ops = GraphQLOperations(client, GRAPHQL_URL)

        assert abs(ops._now_timestamp() - datetime.now(tz=UTC).timestamp()) < 5


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
