"""Tests for the v2 (GraphQL) goal operations."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.base import MILESTONES_CONNECTION
from bloomy.v2.models import Goal, GoalStatus
from bloomy.v2.operations.goal import AsyncGoalOperations, GoalOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

MILESTONE_NODE = {
    "id": 6440354,
    "goalId": 5265048,
    "title": "SDK v2 test milestone",
    "dueDate": 1767225600,
    "completed": False,
    "status": None,
    "dateCreated": 1790278069,
}

GOAL_NODE = {
    "id": 5265048,
    "title": "SDK v2 test goal",
    "status": "ON_TRACK",
    "dueDate": 1798761600,
    "archived": False,
    "archivedTimestamp": None,
    "dateCreated": 1790278069,
    "notesId": "pad-1",
    "notesText": "some notes\n",
    "localHtml": None,
    "collaborationEnabled": True,
    "assignee": {"id": 1305290, "fullName": "Fran Orozco"},
    "meetings": {"nodes": [{"id": 349524, "name": "v2 API"}]},
    "milestones": {"nodes": [MILESTONE_NODE]},
}


def _response(json_data: object) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = Mock()
    return response


def _async_response(json_data: object) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


class TestGoalOperationsSync:
    """Tests for the sync `GoalOperations`."""

    def test_details(self) -> None:
        """`details()` returns a transformed `Goal`, including milestones and notes."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"goal": GOAL_NODE}})

        result = ops.details(5265048)

        assert isinstance(result, Goal)
        assert result.id == 5265048
        assert result.owner is not None and result.owner.id == 1305290
        assert result.status == GoalStatus.ON_TRACK
        assert result.notes == "some notes"
        assert len(result.milestones) == 1
        assert result.milestones[0].id == 6440354
        assert len(result.meetings) == 1
        assert result.meetings[0].id == 349524
        # Transforms: unix-seconds timestamps become UTC-aware datetimes.
        assert result.created_date.tzinfo is not None
        assert result.due_date is not None and result.due_date.tzinfo is not None

    def test_details_with_null_assignee(self) -> None:
        """A goal with a `null` `assignee` produces `owner=None`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        node = {**GOAL_NODE, "assignee": None}
        client.post.return_value = _response({"data": {"goal": node}})

        result = ops.details(5265048)

        assert result.owner is None

    def test_details_raises_when_goal_is_null(self) -> None:
        """`details()` raises `GraphQLError` when `goal` is `null` (unknown id)."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"goal": None}})

        with pytest.raises(GraphQLError, match="Goal 999999999 not found"):
            ops.details(999999999)

    def test_list_by_meeting_default_where(self) -> None:
        """`list(meeting_id=...)` filters archived goals out by default."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"goals": {"nodes": [GOAL_NODE]}}}}
        )

        result = ops.list(meeting_id=349524)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {"and": [{"archived": {"eq": False}}]}

    def test_list_by_user_uses_user_goals_connection(self) -> None:
        """`list(user_id=...)` queries `user(id){ goals }`, not root `goals(userId)`.

        Root `goals(userId)` unconditionally excludes archived goals
        regardless of `where` (verified live), so `user(id){ goals }` is
        used instead to make `include_archived` work.
        """
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"user": {"goals": {"nodes": [GOAL_NODE]}}}}
        )

        result = ops.list(user_id=1305290, include_archived=True)

        assert len(result) == 1
        sent_query = client.post.call_args.kwargs["json"]["query"]
        assert "goals(userId:" not in sent_query
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["userId"] == 1305290
        assert variables["where"] is None

    def test_list_defaults_to_current_user(self) -> None:
        """`list()` with neither id defaults to the current user."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"user": {"goals": {"nodes": []}}}}),
        ]

        ops.list()

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["userId"] == 1305290

    def test_list_both_ids_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)

        with pytest.raises(
            ValueError, match="Cannot specify both meeting_id and user_id"
        ):
            ops.list(meeting_id=349524, user_id=1305290)

        assert client.post.call_count == 0

    def test_create_defaults(self) -> None:
        """`create()` defaults the due date to 90 days out and attaches the meeting."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        result = ops.create(349524, "SDK v2 test goal", user_id=1305290)

        assert result.id == 5265048
        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        input_ = create_variables["input"]
        assert input_["title"] == "SDK v2 test goal"
        assert input_["assignee"] == 1305290
        assert input_["status"] == "ON_TRACK"
        assert input_["meetingsAndPlans"] == [
            {"meetingId": 349524, "addToDepartmentPlan": False}
        ]
        assert isinstance(input_["dueDate"], float)
        assert "notesId" not in input_
        assert "milestones" not in input_

    def test_create_default_due_date_is_90_days_from_today_utc(self) -> None:
        """The default due date is 90 days from today, at 00:00 UTC.

        Not the local calendar date: `date.today()` can differ from the UTC
        date near a day boundary.
        """
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.create(349524, "SDK v2 test goal", user_id=1305290)

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        due_date = datetime.fromtimestamp(create_variables["input"]["dueDate"], tz=UTC)
        expected_date = (datetime.now(tz=UTC) + timedelta(days=90)).date()
        assert due_date.date() == expected_date
        assert due_date.time() == datetime.min.time()

    def test_create_raises_when_create_goal_id_is_zero(self) -> None:
        """`create()` raises `GraphQLError` when `CreateGoal` returns id `0`.

        A failed `CreateGoal` returns `IdModel(0)` rather than a top-level
        GraphQL error.
        """
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"CreateGoal": {"id": 0}}})

        with pytest.raises(GraphQLError, match="create goal failed"):
            ops.create(349524, "SDK v2 test goal", user_id=1305290)

        assert client.post.call_count == 1

    def test_create_with_notes_calls_create_note_first(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateGoal`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-99"}}}),
            _response({"data": {"CreateGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.create(349524, "SDK v2 test goal", user_id=1305290, notes="hello")

        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["notesId"] == "pad-99"
        assert create_variables["input"]["collaborationEnabled"] is True

    def test_create_with_milestones_dicts_and_tuples(self) -> None:
        """`create(milestones=...)` accepts both dicts and tuples."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.create(
            349524,
            "SDK v2 test goal",
            user_id=1305290,
            milestones=[
                {"title": "M1", "due_date": 1767225600},
                ("M2", 1767225600, True),
                {"title": "M3", "due_date": date(2026, 1, 1), "completed": True},
                ("M4", datetime(2026, 1, 1, tzinfo=UTC)),
            ],
        )

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        milestones = create_variables["input"]["milestones"]
        assert milestones == [
            {"title": "M1", "dueDate": 1767225600.0, "completed": False},
            {"title": "M2", "dueDate": 1767225600.0, "completed": True},
            {"title": "M3", "dueDate": 1767225600.0, "completed": True},
            {"title": "M4", "dueDate": 1767225600.0, "completed": False},
        ]

    def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"CreateGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.create(349524, "SDK v2 test goal")

        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["assignee"] == 1305290

    def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            ops.update(5265048)

    def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        result = ops.update(5265048, title="New title")

        assert result.id == 5265048
        edit_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"goalId": 5265048, "title": "New title"}}

    def test_update_status_and_due_date(self) -> None:
        """`update(status=..., due_date=...)` sends both as GraphQL-shaped values."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.update(5265048, status=GoalStatus.OFF_TRACK, due_date=1799000000)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input["status"] == "OFF_TRACK"
        assert edit_input["dueDate"] == 1799000000.0

    def test_archive_success(self) -> None:
        """`archive()` sends `archived: true` and confirms the re-read is archived."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": {**GOAL_NODE, "archived": True}}}),
        ]

        result = ops.archive(5265048)

        assert result.archived is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"goalId": 5265048, "archived": True}

    def test_archive_raises_when_still_not_archived(self) -> None:
        """`archive()` raises `GraphQLError` if the re-read is still not archived.

        `EditGoal{archived: true}` can report success without archiving
        anything (verified live: an un-awaited detach call can swallow its
        own exceptions server-side).
        """
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),  # archived: False
        ]

        with pytest.raises(GraphQLError, match="still not archived"):
            ops.archive(5265048)

    def test_restore(self) -> None:
        """`restore()` sends `archived: false`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.restore(5265048)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"goalId": 5265048, "archived": False}

    def test_update_user_id_and_notes(self) -> None:
        """`update(user_id=..., notes=...)` sends `assignee` and calls `CreateNote`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-42"}}}),
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.update(5265048, user_id=999, notes="Updated notes")

        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "goalId": 5265048,
            "assignee": 999,
            "notesId": "pad-42",
            "collaborationEnabled": True,
        }

    def test_update_due_date_accepts_datetime_object(self) -> None:
        """`update(due_date=...)` accepts a `datetime`, not only a unix timestamp."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]
        due_date = datetime(2026, 1, 1, tzinfo=UTC)

        ops.update(5265048, due_date=due_date)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"goalId": 5265048, "dueDate": due_date.timestamp()}

    def test_list_by_meeting_include_archived(self) -> None:
        """`list(meeting_id=..., include_archived=True)` sends an unfiltered `where`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"goals": {"nodes": [GOAL_NODE]}}}}
        )

        ops.list(meeting_id=349524, include_archived=True)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] is None

    def test_list_by_meeting_with_null_meeting_returns_empty(self) -> None:
        """A `null` `meeting` (e.g. an unknown meeting id) yields an empty list."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"meeting": None}})

        result = ops.list(meeting_id=999999)

        assert result == []

    def test_details_with_null_milestones_and_meetings(self) -> None:
        """`null` `milestones`/`meetings` connections validate as empty lists."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        node = {**GOAL_NODE, "milestones": None, "meetings": None}
        client.post.return_value = _response({"data": {"goal": node}})

        result = ops.details(5265048)

        assert result.milestones == []
        assert result.meetings == []

    def test_details_query_selects_milestones_like_milestone_list(self) -> None:
        """The goal query filters and orders milestones as `milestone.list()` does."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"goal": GOAL_NODE}})

        ops.details(5265048)

        sent_query = client.post.call_args.kwargs["json"]["query"]
        assert MILESTONES_CONNECTION in sent_query
        assert "dateDeleted: { eq: null }" in MILESTONES_CONNECTION

    def test_update_notes_only(self) -> None:
        """`update(notes=...)` alone is a valid update and sends only the pad."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-5"}}}),
            _response({"data": {"EditGoal": {"id": 5265048}}}),
            _response({"data": {"goal": GOAL_NODE}}),
        ]

        ops.update(5265048, notes="Only notes")

        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "goalId": 5265048,
            "notesId": "pad-5",
            "collaborationEnabled": True,
        }

    def test_update_raises_when_edit_goal_returns_null(self) -> None:
        """A `null` `EditGoal` result raises `GraphQLError` without a re-read."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"EditGoal": None}})

        with pytest.raises(GraphQLError, match="update goal failed"):
            ops.update(5265048, title="New title")

        assert client.post.call_count == 1

    def test_details_without_milestones_and_meetings(self) -> None:
        """A goal payload without `milestones`/`meetings` keys yields empty lists."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        node = {
            key: value
            for key, value in GOAL_NODE.items()
            if key not in ("milestones", "meetings")
        }
        client.post.return_value = _response({"data": {"goal": node}})

        result = ops.details(5265048)

        assert result.milestones == []
        assert result.meetings == []

    def test_create_with_notes_failure_raises(self) -> None:
        """A failed `CreateNote` call raises `GraphQLError` before `CreateGoal` runs."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "CreateNote": {
                        "success": False,
                        "message": "note failed",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="note failed"):
            ops.create(349524, "SDK v2 test goal", user_id=1305290, notes="hello")

        assert client.post.call_count == 1

    def test_details_raises_graphql_error_on_http_400_with_errors(self) -> None:
        """A body with a top-level `errors` array raises `GraphQLError` on HTTP 400."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"errors": [{"message": "Goal not found"}]}
        response.raise_for_status = Mock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="Goal not found") as exc_info:
            ops.details(5265048)

        assert exc_info.value.status_code == 400
        response.raise_for_status.assert_not_called()

    def test_list_raises_graphql_error_on_200_with_errors(self) -> None:
        """A 200 body with a top-level `errors` array still raises `GraphQLError`."""
        client = Mock()
        ops = GoalOperations(client, GRAPHQL_URL)
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": None,
            "errors": [{"message": "execution failed"}],
        }
        response.raise_for_status = Mock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="execution failed"):
            ops.list(meeting_id=349524)


class TestGoalOperationsAsync:
    """Tests for the async `AsyncGoalOperations`."""

    @pytest.mark.asyncio
    async def test_details(self) -> None:
        """`details()` returns a transformed `Goal`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"goal": GOAL_NODE}})

        result = await ops.details(5265048)

        assert result.id == 5265048
        assert result.notes == "some notes"
        assert len(result.milestones) == 1

    @pytest.mark.asyncio
    async def test_details_raises_when_goal_is_null(self) -> None:
        """`details()` raises `GraphQLError` when `goal` is `null`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"goal": None}})

        with pytest.raises(GraphQLError, match="Goal 999999999 not found"):
            await ops.details(999999999)

    @pytest.mark.asyncio
    async def test_list_both_ids_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)

        with pytest.raises(
            ValueError, match="Cannot specify both meeting_id and user_id"
        ):
            await ops.list(meeting_id=349524, user_id=1305290)

        assert client.post.call_count == 0

    @pytest.mark.asyncio
    async def test_list_by_user_include_archived(self) -> None:
        """`list(user_id=..., include_archived=True)` skips the auth lookup."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"user": {"goals": {"nodes": [GOAL_NODE]}}}}
        )

        result = await ops.list(user_id=1305290, include_archived=True)

        assert [goal.id for goal in result] == [5265048]
        assert client.post.call_count == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"userId": 1305290, "where": None}

    @pytest.mark.asyncio
    async def test_update_raises_when_edit_goal_returns_null(self) -> None:
        """A `null` `EditGoal` result raises `GraphQLError` without a re-read."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"EditGoal": None}})

        with pytest.raises(GraphQLError, match="restore goal failed"):
            await ops.restore(5265048)

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_list_by_meeting(self) -> None:
        """`list(meeting_id=...)` queries `meeting(id){ goals }`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"meeting": {"goals": {"nodes": [GOAL_NODE]}}}}
        )

        result = await ops.list(meeting_id=349524)

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {"and": [{"archived": {"eq": False}}]}

    @pytest.mark.asyncio
    async def test_list_by_user_defaults_to_current_user(self) -> None:
        """`list()` with neither id fetches and uses the authenticated user's id."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"user": {"goals": {"nodes": [GOAL_NODE]}}}}),
        ]

        result = await ops.list()

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["userId"] == 1305290

    @pytest.mark.asyncio
    async def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            await ops.update(5265048)

    @pytest.mark.asyncio
    async def test_update_full_fields(self) -> None:
        """`update()` with every field sends each and re-reads the goal."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-7"}}}
            ),
            _async_response({"data": {"EditGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": GOAL_NODE}}),
        ]

        result = await ops.update(
            5265048,
            title="New title",
            status=GoalStatus.OFF_TRACK,
            due_date=1799000000,
            user_id=999,
            notes="Updated notes",
        )

        assert result.id == 5265048
        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {
            "goalId": 5265048,
            "title": "New title",
            "status": "OFF_TRACK",
            "dueDate": 1799000000.0,
            "assignee": 999,
            "notesId": "pad-7",
            "collaborationEnabled": True,
        }

    @pytest.mark.asyncio
    async def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"CreateGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": GOAL_NODE}}),
        ]

        await ops.create(349524, "SDK v2 test goal")

        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["assignee"] == 1305290

    @pytest.mark.asyncio
    async def test_create_raises_when_create_goal_id_is_zero(self) -> None:
        """`create()` raises `GraphQLError` when `CreateGoal` returns id `0`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"CreateGoal": {"id": 0}}})

        with pytest.raises(GraphQLError, match="create goal failed"):
            await ops.create(349524, "SDK v2 test goal", user_id=1305290)

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_create_with_notes_calls_create_note_first(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateGoal`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-99"}}}
            ),
            _async_response({"data": {"CreateGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": GOAL_NODE}}),
        ]

        await ops.create(349524, "SDK v2 test goal", user_id=1305290, notes="hello")

        create_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_variables["input"]["notesId"] == "pad-99"
        assert create_variables["input"]["collaborationEnabled"] is True

    @pytest.mark.asyncio
    async def test_create_with_milestones(self) -> None:
        """`create(milestones=...)` builds `Goal_MilestoneCreateModelInput` entries."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": GOAL_NODE}}),
        ]

        await ops.create(
            349524,
            "SDK v2 test goal",
            user_id=1305290,
            milestones=[("M1", 1767225600)],
        )

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables["input"]["milestones"] == [
            {"title": "M1", "dueDate": 1767225600.0, "completed": False}
        ]

    @pytest.mark.asyncio
    async def test_archive_success(self) -> None:
        """`archive()` returns the re-read goal once it is confirmed archived."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": {**GOAL_NODE, "archived": True}}}),
        ]

        result = await ops.archive(5265048)

        assert result.archived is True
        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"goalId": 5265048, "archived": True}

    @pytest.mark.asyncio
    async def test_archive_raises_when_still_not_archived(self) -> None:
        """`archive()` raises `GraphQLError` if the re-read is still not archived."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": GOAL_NODE}}),  # archived: False
        ]

        with pytest.raises(GraphQLError, match="still not archived"):
            await ops.archive(5265048)

    @pytest.mark.asyncio
    async def test_restore(self) -> None:
        """`restore()` sends `archived: false`."""
        client = AsyncMock()
        ops = AsyncGoalOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditGoal": {"id": 5265048}}}),
            _async_response({"data": {"goal": GOAL_NODE}}),
        ]

        await ops.restore(5265048)

        edit_input = client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
        assert edit_input == {"goalId": 5265048, "archived": False}
