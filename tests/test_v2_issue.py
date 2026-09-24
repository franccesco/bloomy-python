"""Tests for the v2 (GraphQL) issue operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.models import Issue
from bloomy.v2.operations.issue import AsyncIssueOperations, IssueOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

ISSUE_NODE = {
    "id": 28471978,
    "title": "SDK v2 test issue",
    "recurrenceId": 349524,
    "addToDepartmentPlan": False,
    "notesId": "pad-1",
    "notesText": "some notes\n",
    "localHtml": None,
    "collaborationEnabled": True,
    "completed": False,
    "completedTimestamp": None,
    "archived": False,
    "archivedTimestamp": None,
    "dateCreated": 1790275733,
    "priorityVoteRank": 999,
    "numStarVotes": 0,
    "issueNumber": 1,
    "assignee": {"id": 1305290, "fullName": "Fran Orozco"},
    "meeting": {"id": 349524, "name": "v2 API"},
}


def _response(json_data: object) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


class TestIssueOperationsSync:
    """Tests for the sync `IssueOperations`."""

    def test_details(self) -> None:
        """`details()` returns a transformed `Issue`, including plain-text notes."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"issue": ISSUE_NODE}})

        result = ops.details(28471978)

        assert isinstance(result, Issue)
        assert result.id == 28471978
        assert result.owner is not None and result.owner.id == 1305290
        assert result.meeting is not None and result.meeting.id == 349524
        assert result.notes == "some notes"

    def test_details_with_null_assignee(self) -> None:
        """An issue with a `null` `assignee` produces `owner=None`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        node = {**ISSUE_NODE, "assignee": None}
        client.post.return_value = _response({"data": {"issue": node}})

        result = ops.details(28471978)

        assert result.owner is None

    @pytest.mark.parametrize(
        ("raw_archived", "long_term", "expected"),
        [
            (True, True, False),  # listed on the Long-Term tab
            (True, False, True),  # archived (incl. an archived long-term issue)
            (False, False, False),
        ],
    )
    def test_archived_ignores_long_term_archived_flag(
        self, raw_archived: bool, long_term: bool, expected: bool
    ) -> None:
        """Long-term issues are not reported as archived."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        node = {
            **ISSUE_NODE,
            "archived": raw_archived,
            "addToDepartmentPlan": long_term,
        }
        client.post.return_value = _response({"data": {"issue": node}})

        result = ops.details(28471978)

        assert result.archived is expected
        assert result.long_term is long_term

    def test_list_short_term_default_where(self) -> None:
        """`list()` filters short-term, open, non-sent-away issues by default."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"issues": {"nodes": [ISSUE_NODE]}}}}
        )

        result = ops.list(349524)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {
            "and": [
                {"addToDepartmentPlan": {"eq": False}},
                {"sentToIssueMeetingName": {"eq": None}},
            ]
        }

    def test_list_long_term_uses_long_term_issues_connection(self) -> None:
        """`list(long_term=True)` queries `longTermIssues`, not `issues`.

        `meeting.issues` drops archived issues server-side, and the API stores
        long-term issues as archived, so `issues` never returns them.
        """
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"longTermIssues": {"nodes": [ISSUE_NODE]}}}}
        )

        result = ops.list(349524, long_term=True)

        assert len(result) == 1
        sent_query = client.post.call_args.kwargs["json"]["query"]
        assert "longTermIssues" in sent_query
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] == {"and": [{"addToDepartmentPlan": {"eq": True}}]}

    def test_list_include_solved_merges_and_dedupes(self) -> None:
        """`include_solved=True` merges `recentlySolvedIssues`, deduping by id."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"meeting": {"issues": {"nodes": [ISSUE_NODE]}}}}),
            _response(
                {
                    "data": {
                        "meeting": {
                            "recentlySolvedIssues": {
                                "nodes": [{**ISSUE_NODE, "completed": True}]
                            }
                        }
                    }
                }
            ),
        ]

        result = ops.list(349524, include_solved=True)

        assert len(result) == 1
        assert client.post.call_count == 2

    def test_list_include_archived(self) -> None:
        """`include_archived=True` merges `archivedIssues`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        archived_node = {**ISSUE_NODE, "id": 999, "archived": True}
        client.post.side_effect = [
            _response({"data": {"meeting": {"issues": {"nodes": []}}}}),
            _response(
                {"data": {"meeting": {"archivedIssues": {"nodes": [archived_node]}}}}
            ),
        ]

        result = ops.list(349524, include_archived=True)

        assert len(result) == 1
        assert result[0].id == 999

    def test_create_without_notes(self) -> None:
        """`create()` without notes skips `CreateNote` and reads back details."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateIssue": {"id": 28471978}}}),
            _response({"data": {"issue": ISSUE_NODE}}),
        ]

        result = ops.create(349524, "SDK v2 test issue", user_id=1305290)

        assert result.id == 28471978
        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables == {
            "input": {
                "title": "SDK v2 test issue",
                "ownerId": 1305290,
                "recurrenceId": 349524,
                "addToDepartmentPlan": False,
            }
        }

    def test_create_with_notes_calls_create_note_first(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateIssue`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-99"}}}),
            _response({"data": {"CreateIssue": {"id": 28471978}}}),
            _response({"data": {"issue": ISSUE_NODE}}),
        ]

        ops.create(349524, "SDK v2 test issue", user_id=1305290, notes="hello")

        create_issue_variables = client.post.call_args_list[1].kwargs["json"][
            "variables"
        ]
        assert create_issue_variables["input"]["notesId"] == "pad-99"
        assert create_issue_variables["input"]["collaborationEnabled"] is True

    def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"CreateIssue": {"id": 28471978}}}),
            _response({"data": {"issue": ISSUE_NODE}}),
        ]

        ops.create(349524, "SDK v2 test issue")

        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["ownerId"] == 1305290

    def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            ops.update(28471978)

    def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditIssue": {"success": True, "message": None}}}),
            _response({"data": {"issue": ISSUE_NODE}}),
        ]

        result = ops.update(28471978, title="New title")

        assert result.id == 28471978
        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"id": 28471978, "title": "New title"}}

    def test_update_raises_graphql_error_on_failure(self) -> None:
        """`update()` raises `GraphQLError` when `EditIssue` reports failure."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
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
            ops.update(28471978, title="New title")

    def test_solve(self) -> None:
        """`solve()` sends `completed: true` with a current timestamp."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditIssue": {"success": True, "message": None}}}),
            _response({"data": {"issue": {**ISSUE_NODE, "completed": True}}}),
        ]

        result = ops.solve(28471978)

        assert result.completed is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input["id"] == 28471978
        assert edit_input["completed"] is True
        assert isinstance(edit_input["completedTimestamp"], float)

    def test_reopen(self) -> None:
        """`reopen()` sends `completed: false, completedTimestamp: null`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditIssue": {"success": True, "message": None}}}),
            _response({"data": {"issue": ISSUE_NODE}}),
        ]

        ops.reopen(28471978)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "id": 28471978,
            "completed": False,
            "completedTimestamp": None,
        }

    def test_archive(self) -> None:
        """`archive()` sends `archived: true`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditIssue": {"success": True, "message": None}}}),
            _response({"data": {"issue": {**ISSUE_NODE, "archived": True}}}),
        ]

        result = ops.archive(28471978)

        assert result.archived is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"id": 28471978, "archived": True}

    def test_restore(self) -> None:
        """`restore()` sends `archived: false`."""
        client = Mock()
        ops = IssueOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditIssue": {"success": True, "message": None}}}),
            _response({"data": {"issue": ISSUE_NODE}}),
        ]

        ops.restore(28471978)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"id": 28471978, "archived": False}


class TestIssueOperationsAsync:
    """Tests for the async `AsyncIssueOperations`."""

    @pytest.mark.asyncio
    async def test_details(self) -> None:
        """`details()` returns a transformed `Issue`."""
        client = AsyncMock()
        ops = AsyncIssueOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"data": {"issue": ISSUE_NODE}}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        result = await ops.details(28471978)

        assert result.id == 28471978
        assert result.notes == "some notes"

    @pytest.mark.asyncio
    async def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncIssueOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            await ops.update(28471978)

    @pytest.mark.asyncio
    async def test_create_with_notes(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateIssue`."""
        client = AsyncMock()
        ops = AsyncIssueOperations(client, GRAPHQL_URL)

        note_response = MagicMock()
        note_response.status_code = 200
        note_response.json.return_value = {
            "data": {"CreateNote": {"success": True, "data": "pad-99"}}
        }
        note_response.raise_for_status = MagicMock()

        create_response = MagicMock()
        create_response.status_code = 200
        create_response.json.return_value = {"data": {"CreateIssue": {"id": 28471978}}}
        create_response.raise_for_status = MagicMock()

        details_response = MagicMock()
        details_response.status_code = 200
        details_response.json.return_value = {"data": {"issue": ISSUE_NODE}}
        details_response.raise_for_status = MagicMock()

        client.post.side_effect = [note_response, create_response, details_response]

        result = await ops.create(
            349524, "SDK v2 test issue", user_id=1305290, notes="hello"
        )

        assert result.id == 28471978
        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["notesId"] == "pad-99"

    @pytest.mark.asyncio
    async def test_solve_reopen_archive_restore(self) -> None:
        """Each single-field mutation sends only its own field."""
        client = AsyncMock()
        ops = AsyncIssueOperations(client, GRAPHQL_URL)

        def edit_ok() -> MagicMock:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {
                "data": {"EditIssue": {"success": True, "message": None}}
            }
            response.raise_for_status = MagicMock()
            return response

        def details() -> MagicMock:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"data": {"issue": ISSUE_NODE}}
            response.raise_for_status = MagicMock()
            return response

        client.post.side_effect = [
            edit_ok(),
            details(),
            edit_ok(),
            details(),
            edit_ok(),
            details(),
            edit_ok(),
            details(),
        ]

        await ops.solve(28471978)
        await ops.reopen(28471978)
        await ops.archive(28471978)
        await ops.restore(28471978)

        assert client.post.call_count == 8
