"""Tests for the v2 (GraphQL) metric operations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.models import Metric
from bloomy.v2.operations.metric import AsyncMetricOperations, MetricOperations

GRAPHQL_URL = "https://app.bloomgrowth.com/graphql/"

METRIC_NODE = {
    "measurableId": 2036155,
    "title": "SDK v2 test metric",
    "units": "NONE",
    "rule": "GREATER_THAN",
    "frequency": "WEEKLY",
    "singleGoalValue": "100.00000",
    "minGoalValue": "100.00000",
    "maxGoalValue": None,
    "archived": False,
    "metricType": "METRIC",
    "notesId": None,
    "notesText": "",
    "localHtml": None,
    "collaborationEnabled": False,
    "dateCreated": 1790278038,
    "isExternallySynced": False,
    "assignee": {"id": 1305290, "fullName": "Fran Orozco"},
}

DIVIDER_NODE = {
    "measurableId": 0,
    "title": None,
    "units": "NONE",
    "rule": "GREATER_THAN",
    "frequency": "WEEKLY",
    "singleGoalValue": None,
    "minGoalValue": None,
    "maxGoalValue": None,
    "archived": False,
    "metricType": "DIVIDER",
    "notesId": "0",
    "notesText": "",
    "localHtml": None,
    "collaborationEnabled": False,
    "dateCreated": 1790278038,
    "isExternallySynced": False,
    "assignee": None,
}

SCORE_NODE = {
    "id": 499964609,
    "value": "123.00000",
    "timestamp": 1789862400,
    "notesText": "probe note",
    "measurableId": 2036155,
}

EMPTY_SCORE_NODE = {
    "id": 499964591,
    "value": "",
    "timestamp": 1778976000,
    "notesText": None,
    "measurableId": 2036155,
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


class TestMetricOperationsSync:
    """Tests for the sync `MetricOperations`."""

    def test_details(self) -> None:
        """`details()` returns a transformed `Metric`, id from `measurableId`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"metric": METRIC_NODE}})

        result = ops.details(2036155)

        assert isinstance(result, Metric)
        assert result.id == 2036155
        assert result.owner is not None and result.owner.id == 1305290
        assert result.goal == 100.0
        assert result.notes is None

    def test_list_meeting_filters_divider_and_sets_where(self) -> None:
        """`list(meeting_id=...)` filters DIVIDER rows and archived metrics."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"metrics": {"nodes": [METRIC_NODE, DIVIDER_NODE]}}}}
        )

        result = ops.list(meeting_id=349524)

        assert len(result) == 1
        assert result[0].id == 2036155
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {
            "and": [
                {"archived": {"eq": False}},
                {"metricType": {"eq": "METRIC"}},
            ]
        }

    def test_list_with_frequency_adds_condition(self) -> None:
        """`list(frequency=...)` adds a `frequency` condition to `where`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"meeting": {"metrics": {"nodes": []}}}}
        )

        ops.list(meeting_id=349524, frequency="DAILY")

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert {"frequency": {"eq": "DAILY"}} in variables["where"]["and"]

    def test_list_both_meeting_and_user_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="not both"):
            ops.list(meeting_id=349524, user_id=1305290)

    def test_list_defaults_to_current_user(self) -> None:
        """`list()` with neither id fetches the authenticated user first."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"user": {"metrics": {"nodes": [METRIC_NODE]}}}}),
        ]

        result = ops.list()

        assert len(result) == 1
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["userId"] == 1305290

    def test_create_defaults(self) -> None:
        """`create()` sends the expected default input and reads back details."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        result = ops.create(349524, "SDK v2 test metric", user_id=1305290, goal=100)

        assert result.id == 2036155
        create_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_vars["input"] == {
            "title": "SDK v2 test metric",
            "assignee": 1305290,
            "units": "NONE",
            "rule": "GREATER_THAN",
            "frequency": "WEEKLY",
            "averageOverrideType": "NONE",
            "meetings": [349524],
            "customGoals": [],
            "singleGoalValue": "100",
        }

    def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _response({"data": {"CreateMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        ops.create(349524, "SDK v2 test metric")

        create_vars = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_vars["input"]["assignee"] == 1305290

    def test_create_with_notes_calls_create_note_first(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateMetric`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-99"}}}),
            _response({"data": {"CreateMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        ops.create(349524, "SDK v2 test metric", user_id=1305290, notes="hello")

        create_vars = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_vars["input"]["notesId"] == "pad-99"
        assert create_vars["input"]["collaborationEnabled"] is True

    def test_create_between_uses_min_max(self) -> None:
        """`create(rule=BETWEEN, min_goal=..., max_goal=...)` sends the range goal."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        ops.create(
            349524,
            "SDK v2 test metric",
            user_id=1305290,
            rule="BETWEEN",
            min_goal=10,
            max_goal=20,
        )

        create_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_vars["input"]["minGoalValue"] == "10"
        assert create_vars["input"]["maxGoalValue"] == "20"
        assert "singleGoalValue" not in create_vars["input"]

    def test_create_goal_with_between_raises(self) -> None:
        """`create(rule=BETWEEN, goal=...)` raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="BETWEEN"):
            ops.create(
                349524, "SDK v2 test metric", user_id=1305290, rule="BETWEEN", goal=10
            )

    def test_create_min_goal_without_between_raises(self) -> None:
        """`create(min_goal=..., rule != BETWEEN)` raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="BETWEEN"):
            ops.create(349524, "SDK v2 test metric", user_id=1305290, min_goal=10)

    def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            ops.update(2036155)

    def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        result = ops.update(2036155, title="New title")

        assert result.id == 2036155
        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {"metricId": 2036155, "title": "New title"}

    def test_update_goal_conflict_raises(self) -> None:
        """`update(rule=BETWEEN, goal=...)` raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="BETWEEN"):
            ops.update(2036155, rule="BETWEEN", goal=10)

    def test_archive(self) -> None:
        """`archive()` sends `archived: true`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditMetric": {"id": 2036155}}}),
            _response({"data": {"metric": {**METRIC_NODE, "archived": True}}}),
        ]

        result = ops.archive(2036155)

        assert result.archived is True
        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {"metricId": 2036155, "archived": True}

    def test_scores_filters_empty_by_default(self) -> None:
        """`scores()` skips empty placeholder rows unless `include_empty=True`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"metric": {"scoresNonPaginated": [SCORE_NODE, EMPTY_SCORE_NODE]}}}
        )

        result = ops.scores(2036155)

        assert len(result) == 1
        assert result[0].value == 123.0

    def test_scores_include_empty(self) -> None:
        """`scores(include_empty=True)` keeps empty placeholder rows."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"metric": {"scoresNonPaginated": [SCORE_NODE, EMPTY_SCORE_NODE]}}}
        )

        result = ops.scores(2036155, include_empty=True)

        assert len(result) == 2
        assert result[1].value is None

    def test_scores_start_end_builds_where(self) -> None:
        """`scores(start=..., end=...)` builds a timestamp range `where`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"metric": {"scoresNonPaginated": []}}}
        )

        ops.scores(2036155, start=1000, end=2000)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] == {
            "and": [{"timestamp": {"gte": 1000.0}}, {"timestamp": {"lte": 2000.0}}]
        }

    def test_set_score_success(self) -> None:
        """`set_score()` creates and re-reads the score."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateMetricScore": {"id": 499964609}}}),
            _response({"data": {"metric": {"scoresNonPaginated": [SCORE_NODE]}}}),
        ]

        result = ops.set_score(2036155, 123, 1790278038)

        assert result.id == 499964609
        assert result.value == 123.0
        create_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_vars["input"] == {
            "metricId": 2036155,
            "value": "123",
            "timestamp": 1790278038.0,
        }

    def test_set_score_unparseable_value_raises(self) -> None:
        """`set_score()` raises `GraphQLError` when the value is unparseable."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"CreateMetricScore": None}})

        with pytest.raises(GraphQLError, match="could not be parsed"):
            ops.set_score(2036155, "not-a-number", 1790278038)

    def test_set_score_daily_duplicate_falls_back_to_edit(self) -> None:
        """DAILY "already exists" falls back to finding and editing the score."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        daily_node = {**SCORE_NODE, "id": 1, "value": "", "timestamp": 1790208001}
        client.post.side_effect = [
            _response(
                {
                    "errors": [
                        {
                            "message": "Unexpected Execution Error",
                            "extensions": {
                                "message": (
                                    "A score for this measurable and date "
                                    "already exists."
                                )
                            },
                        }
                    ],
                    "data": {"CreateMetricScore": None},
                }
            ),
            _response({"data": {"metric": {"scoresNonPaginated": [daily_node]}}}),
            _response({"data": {"EditMetricScore": {"id": 1}}}),
            _response(
                {
                    "data": {
                        "metric": {
                            "scoresNonPaginated": [{**daily_node, "value": "42.00000"}]
                        }
                    }
                }
            ),
        ]

        result = ops.set_score(2036158, 42, 1790208001)

        assert result.id == 1
        assert result.value == 42.0
        assert client.post.call_count == 4
        edit_vars = client.post.call_args_list[2].kwargs["json"]["variables"]
        assert edit_vars["input"] == {"id": 1, "value": "42"}

    def test_set_score_other_graphql_error_propagates(self) -> None:
        """A `GraphQLError` unrelated to duplicates is re-raised as-is."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"errors": [{"message": "PermissionsException: nope"}]}
        )

        with pytest.raises(GraphQLError, match="nope"):
            ops.set_score(2036155, 1, 1790278038)

    def test_update_score_value_and_notes(self) -> None:
        """`update_score()` sends both `value` and `notesText`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditMetricScore": {"id": 499964609}}}),
            _response(
                {
                    "data": {
                        "metric": {
                            "scoresNonPaginated": [
                                {**SCORE_NODE, "value": "125.00000", "notesText": "hi"}
                            ]
                        }
                    }
                }
            ),
        ]

        result = ops.update_score(2036155, 499964609, value=125, notes="hi")

        assert result.value == 125.0
        assert result.notes == "hi"
        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {
            "id": 499964609,
            "value": "125",
            "notesText": "hi",
        }

    def test_update_score_requires_a_field(self) -> None:
        """`update_score()` with neither `value` nor `notes` raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one of"):
            ops.update_score(2036155, 499964609)

    def test_update_score_not_found_after_write_raises(self) -> None:
        """A re-read that comes back empty raises `GraphQLError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditMetricScore": {"id": 1}}}),
            _response({"data": {"metric": {"scoresNonPaginated": []}}}),
        ]

        with pytest.raises(GraphQLError, match="not found"):
            ops.update_score(2036155, 999, value=1)

    def test_clear_score(self) -> None:
        """`clear_score()` sends `value: null` and returns `value=None`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditMetricScore": {"id": 499964609}}}),
            _response(
                {
                    "data": {
                        "metric": {"scoresNonPaginated": [{**SCORE_NODE, "value": ""}]}
                    }
                }
            ),
        ]

        result = ops.clear_score(2036155, 499964609)

        assert result.value is None
        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {"id": 499964609, "value": None}

    def test_details_notes_and_dates(self) -> None:
        """`details()` extracts notes and returns a UTC-aware `created_date`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        node = {
            **METRIC_NODE,
            "notesId": "pad-1",
            "notesText": "Metric notes",
            "collaborationEnabled": True,
        }
        client.post.return_value = _response({"data": {"metric": node}})

        result = ops.details(2036155)

        assert result.notes == "Metric notes"
        assert result.notes_id == "pad-1"
        assert result.created_date.tzinfo is not None

    def test_list_meeting_missing_returns_empty(self) -> None:
        """`list(meeting_id=...)` returns `[]` when the meeting itself is `null`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"meeting": None}})

        result = ops.list(meeting_id=349524)

        assert result == []

    def test_list_user_missing_returns_empty(self) -> None:
        """`list(user_id=...)` returns `[]` when the user itself is `null`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"user": None}})

        result = ops.list(user_id=1305290)

        assert result == []

    def test_details_raises_graphql_error_on_http_400(self) -> None:
        """A response with a top-level `errors` array raises `GraphQLError` on 400."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"errors": [{"message": "Metric not found"}]}
        response.raise_for_status = Mock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="Metric not found") as exc_info:
            ops.details(999999)

        assert exc_info.value.status_code == 400
        response.raise_for_status.assert_not_called()

    def test_list_raises_graphql_error_on_200_with_errors(self) -> None:
        """A 200 response with a top-level `errors` array also raises `GraphQLError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
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

    def test_create_note_failure_raises(self) -> None:
        """`create(notes=...)` raises `GraphQLError` when `CreateNote` fails."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
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
            ops.create(349524, "SDK v2 test metric", user_id=1305290, notes="hello")

        assert client.post.call_count == 1

    def test_update_user_units_rule_goal(self) -> None:
        """`update()` sends `assignee`/`units`/`rule`/`singleGoalValue` when given."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"EditMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        ops.update(2036155, user_id=42, units="DOLLAR", rule="LESS_THAN", goal=50)

        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {
            "metricId": 2036155,
            "assignee": 42,
            "units": "DOLLAR",
            "rule": "LESS_THAN",
            "singleGoalValue": "50",
        }

    def test_update_with_notes_calls_create_note_first(self) -> None:
        """`update(notes=...)` calls `CreateNote` before `EditMetric`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateNote": {"success": True, "data": "pad-77"}}}),
            _response({"data": {"EditMetric": {"id": 2036155}}}),
            _response({"data": {"metric": METRIC_NODE}}),
        ]

        ops.update(2036155, notes="Updated notes")

        edit_vars = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_vars["input"]["notesId"] == "pad-77"
        assert edit_vars["input"]["collaborationEnabled"] is True

    def test_update_goal_and_min_goal_without_rule_conflict_raises(self) -> None:
        """`update(goal=..., min_goal=...)` without `rule` raises `ValueError`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="cannot be combined"):
            ops.update(2036155, goal=10, min_goal=5)

    def test_scores_no_range_sends_null_where(self) -> None:
        """`scores()` without `start`/`end` sends `where: null`."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"metric": {"scoresNonPaginated": [SCORE_NODE]}}}
        )

        result = ops.scores(2036155)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] is None
        assert result[0].metric_id == 2036155
        assert result[0].week_date is not None
        assert result[0].week_date.tzinfo is not None

    def test_set_score_daily_duplicate_no_existing_score_reraises(self) -> None:
        """If no matching score is found for the day, the original error re-raises."""
        client = Mock()
        ops = MetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response(
                {
                    "errors": [
                        {
                            "message": "Unexpected Execution Error",
                            "extensions": {
                                "message": (
                                    "A score for this measurable and date "
                                    "already exists."
                                )
                            },
                        }
                    ],
                    "data": {"CreateMetricScore": None},
                }
            ),
            _response({"data": {"metric": {"scoresNonPaginated": []}}}),
        ]

        with pytest.raises(GraphQLError, match="Unexpected Execution Error"):
            ops.set_score(2036158, 42, 1790208001)

        assert client.post.call_count == 2


class TestMetricOperationsAsync:
    """Tests for the async `AsyncMetricOperations`."""

    @pytest.mark.asyncio
    async def test_details(self) -> None:
        """`details()` returns a transformed `Metric`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"metric": METRIC_NODE}})

        result = await ops.details(2036155)

        assert result.id == 2036155
        assert isinstance(result, Metric)

    @pytest.mark.asyncio
    async def test_list_both_meeting_and_user_raises(self) -> None:
        """`list()` with both `meeting_id` and `user_id` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="not both"):
            await ops.list(meeting_id=349524, user_id=1305290)

    @pytest.mark.asyncio
    async def test_list_defaults_to_current_user(self) -> None:
        """`list()` with neither id fetches the authenticated user first."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"user": {"metrics": {"nodes": [METRIC_NODE]}}}}),
        ]

        result = await ops.list()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_goal_with_between_raises(self) -> None:
        """`create(rule=BETWEEN, goal=...)` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="BETWEEN"):
            await ops.create(
                349524, "SDK v2 test metric", user_id=1305290, rule="BETWEEN", goal=10
            )

    @pytest.mark.asyncio
    async def test_create_with_notes(self) -> None:
        """`create(notes=...)` calls `CreateNote` before `CreateMetric`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-99"}}}
            ),
            _async_response({"data": {"CreateMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        result = await ops.create(
            349524, "SDK v2 test metric", user_id=1305290, notes="hello"
        )

        assert result.id == 2036155
        create_vars = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_vars["input"]["notesId"] == "pad-99"

    @pytest.mark.asyncio
    async def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            await ops.update(2036155)

    @pytest.mark.asyncio
    async def test_archive(self) -> None:
        """`archive()` sends `archived: true`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": {**METRIC_NODE, "archived": True}}}),
        ]

        result = await ops.archive(2036155)

        assert result.archived is True

    @pytest.mark.asyncio
    async def test_scores_filters_empty_by_default(self) -> None:
        """`scores()` skips empty placeholder rows by default."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"metric": {"scoresNonPaginated": [SCORE_NODE, EMPTY_SCORE_NODE]}}}
        )

        result = await ops.scores(2036155)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_set_score_success(self) -> None:
        """`set_score()` creates and re-reads the score."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateMetricScore": {"id": 499964609}}}),
            _async_response({"data": {"metric": {"scoresNonPaginated": [SCORE_NODE]}}}),
        ]

        result = await ops.set_score(2036155, 123, 1790278038)

        assert result.value == 123.0

    @pytest.mark.asyncio
    async def test_set_score_unparseable_value_raises(self) -> None:
        """`set_score()` raises `GraphQLError` when the value is unparseable."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"CreateMetricScore": None}}
        )

        with pytest.raises(GraphQLError, match="could not be parsed"):
            await ops.set_score(2036155, "not-a-number", 1790278038)

    @pytest.mark.asyncio
    async def test_set_score_daily_duplicate_falls_back_to_edit(self) -> None:
        """DAILY "already exists" falls back to finding and editing the score."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        daily_node = {**SCORE_NODE, "id": 1, "value": "", "timestamp": 1790208001}
        client.post.side_effect = [
            _async_response(
                {
                    "errors": [
                        {
                            "message": "Unexpected Execution Error",
                            "extensions": {
                                "message": (
                                    "A score for this measurable and date "
                                    "already exists."
                                )
                            },
                        }
                    ],
                    "data": {"CreateMetricScore": None},
                }
            ),
            _async_response({"data": {"metric": {"scoresNonPaginated": [daily_node]}}}),
            _async_response({"data": {"EditMetricScore": {"id": 1}}}),
            _async_response(
                {
                    "data": {
                        "metric": {
                            "scoresNonPaginated": [{**daily_node, "value": "42.00000"}]
                        }
                    }
                }
            ),
        ]

        result = await ops.set_score(2036158, 42, 1790208001)

        assert result.value == 42.0
        assert client.post.call_count == 4

    @pytest.mark.asyncio
    async def test_update_score_requires_a_field(self) -> None:
        """`update_score()` with neither `value` nor `notes` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one of"):
            await ops.update_score(2036155, 499964609)

    @pytest.mark.asyncio
    async def test_clear_score(self) -> None:
        """`clear_score()` sends `value: null` and returns `value=None`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditMetricScore": {"id": 499964609}}}),
            _async_response(
                {
                    "data": {
                        "metric": {"scoresNonPaginated": [{**SCORE_NODE, "value": ""}]}
                    }
                }
            ),
        ]

        result = await ops.clear_score(2036155, 499964609)

        assert result.value is None

    @pytest.mark.asyncio
    async def test_list_meeting_filters_divider_and_sets_where(self) -> None:
        """`list(meeting_id=...)` queries `meeting(id){ metrics }`, filters dividers."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"meeting": {"metrics": {"nodes": [METRIC_NODE, DIVIDER_NODE]}}}}
        )

        result = await ops.list(meeting_id=349524)

        assert len(result) == 1
        assert result[0].id == 2036155
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["meetingId"] == 349524
        assert variables["where"] == {
            "and": [
                {"archived": {"eq": False}},
                {"metricType": {"eq": "METRIC"}},
            ]
        }

    @pytest.mark.asyncio
    async def test_list_with_frequency_adds_condition(self) -> None:
        """`list(frequency=...)` adds a `frequency` condition to `where`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"meeting": {"metrics": {"nodes": []}}}}
        )

        await ops.list(meeting_id=349524, frequency="DAILY")

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert {"frequency": {"eq": "DAILY"}} in variables["where"]["and"]

    @pytest.mark.asyncio
    async def test_list_meeting_missing_returns_empty(self) -> None:
        """`list(meeting_id=...)` returns `[]` when the meeting itself is `null`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response({"data": {"meeting": None}})

        result = await ops.list(meeting_id=349524)

        assert result == []

    @pytest.mark.asyncio
    async def test_create_defaults(self) -> None:
        """`create()` sends the expected default input and reads back details."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        result = await ops.create(
            349524, "SDK v2 test metric", user_id=1305290, goal=100
        )

        assert result.id == 2036155
        create_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_vars["input"] == {
            "title": "SDK v2 test metric",
            "assignee": 1305290,
            "units": "NONE",
            "rule": "GREATER_THAN",
            "frequency": "WEEKLY",
            "averageOverrideType": "NONE",
            "meetings": [349524],
            "customGoals": [],
            "singleGoalValue": "100",
        }

    @pytest.mark.asyncio
    async def test_create_defaults_user_id_to_current_user(self) -> None:
        """`create()` without `user_id` fetches the authenticated user first."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"getAuthenticatedUserId": {"id": 1305290}}}),
            _async_response({"data": {"CreateMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        await ops.create(349524, "SDK v2 test metric")

        create_vars = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert create_vars["input"]["assignee"] == 1305290

    @pytest.mark.asyncio
    async def test_create_between_uses_min_max(self) -> None:
        """`create(rule=BETWEEN, min_goal=..., max_goal=...)` sends the range goal."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        await ops.create(
            349524,
            "SDK v2 test metric",
            user_id=1305290,
            rule="BETWEEN",
            min_goal=10,
            max_goal=20,
        )

        create_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_vars["input"]["minGoalValue"] == "10"
        assert create_vars["input"]["maxGoalValue"] == "20"
        assert "singleGoalValue" not in create_vars["input"]

    @pytest.mark.asyncio
    async def test_create_min_goal_without_between_raises(self) -> None:
        """`create(min_goal=..., rule != BETWEEN)` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="BETWEEN"):
            await ops.create(349524, "SDK v2 test metric", user_id=1305290, min_goal=10)

    @pytest.mark.asyncio
    async def test_create_note_failure_raises(self) -> None:
        """`create(notes=...)` raises `GraphQLError` when `CreateNote` fails."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
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
            await ops.create(
                349524, "SDK v2 test metric", user_id=1305290, notes="hello"
            )

    @pytest.mark.asyncio
    async def test_update_title(self) -> None:
        """`update(title=...)` sends only the title field."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        result = await ops.update(2036155, title="New title")

        assert result.id == 2036155
        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {"metricId": 2036155, "title": "New title"}

    @pytest.mark.asyncio
    async def test_update_user_units_rule_goal(self) -> None:
        """`update()` sends `assignee`/`units`/`rule`/`singleGoalValue` when given."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        await ops.update(2036155, user_id=42, units="DOLLAR", rule="LESS_THAN", goal=50)

        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {
            "metricId": 2036155,
            "assignee": 42,
            "units": "DOLLAR",
            "rule": "LESS_THAN",
            "singleGoalValue": "50",
        }

    @pytest.mark.asyncio
    async def test_update_with_notes_calls_create_note_first(self) -> None:
        """`update(notes=...)` calls `CreateNote` before `EditMetric`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"CreateNote": {"success": True, "data": "pad-77"}}}
            ),
            _async_response({"data": {"EditMetric": {"id": 2036155}}}),
            _async_response({"data": {"metric": METRIC_NODE}}),
        ]

        await ops.update(2036155, notes="Updated notes")

        edit_vars = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_vars["input"]["notesId"] == "pad-77"
        assert edit_vars["input"]["collaborationEnabled"] is True

    @pytest.mark.asyncio
    async def test_update_goal_conflict_raises(self) -> None:
        """`update(rule=BETWEEN, goal=...)` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="BETWEEN"):
            await ops.update(2036155, rule="BETWEEN", goal=10)

    @pytest.mark.asyncio
    async def test_update_goal_and_min_goal_without_rule_conflict_raises(
        self,
    ) -> None:
        """`update(goal=..., min_goal=...)` without `rule` raises `ValueError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="cannot be combined"):
            await ops.update(2036155, goal=10, min_goal=5)

    @pytest.mark.asyncio
    async def test_scores_include_empty(self) -> None:
        """`scores(include_empty=True)` keeps empty placeholder rows."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"metric": {"scoresNonPaginated": [SCORE_NODE, EMPTY_SCORE_NODE]}}}
        )

        result = await ops.scores(2036155, include_empty=True)

        assert len(result) == 2
        assert result[1].value is None

    @pytest.mark.asyncio
    async def test_scores_start_end_builds_where(self) -> None:
        """`scores(start=..., end=...)` builds a timestamp range `where`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"metric": {"scoresNonPaginated": []}}}
        )

        await ops.scores(2036155, start=1000, end=2000)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables["where"] == {
            "and": [{"timestamp": {"gte": 1000.0}}, {"timestamp": {"lte": 2000.0}}]
        }

    @pytest.mark.asyncio
    async def test_set_score_daily_duplicate_no_existing_score_reraises(
        self,
    ) -> None:
        """If no matching score is found for the day, the original error re-raises."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {
                    "errors": [
                        {
                            "message": "Unexpected Execution Error",
                            "extensions": {
                                "message": (
                                    "A score for this measurable and date "
                                    "already exists."
                                )
                            },
                        }
                    ],
                    "data": {"CreateMetricScore": None},
                }
            ),
            _async_response({"data": {"metric": {"scoresNonPaginated": []}}}),
        ]

        with pytest.raises(GraphQLError, match="Unexpected Execution Error"):
            await ops.set_score(2036158, 42, 1790208001)

        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_set_score_other_graphql_error_propagates(self) -> None:
        """A `GraphQLError` unrelated to duplicates is re-raised as-is."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"errors": [{"message": "PermissionsException: nope"}]}
        )

        with pytest.raises(GraphQLError, match="nope"):
            await ops.set_score(2036155, 1, 1790278038)

    @pytest.mark.asyncio
    async def test_update_score_value_and_notes(self) -> None:
        """`update_score()` sends both `value` and `notesText`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditMetricScore": {"id": 499964609}}}),
            _async_response(
                {
                    "data": {
                        "metric": {
                            "scoresNonPaginated": [
                                {**SCORE_NODE, "value": "125.00000", "notesText": "hi"}
                            ]
                        }
                    }
                }
            ),
        ]

        result = await ops.update_score(2036155, 499964609, value=125, notes="hi")

        assert result.value == 125.0
        assert result.notes == "hi"
        edit_vars = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert edit_vars["input"] == {
            "id": 499964609,
            "value": "125",
            "notesText": "hi",
        }

    @pytest.mark.asyncio
    async def test_update_score_not_found_after_write_raises(self) -> None:
        """A re-read that comes back empty raises `GraphQLError`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"EditMetricScore": {"id": 1}}}),
            _async_response({"data": {"metric": {"scoresNonPaginated": []}}}),
        ]

        with pytest.raises(GraphQLError, match="not found"):
            await ops.update_score(2036155, 999, value=1)

    @pytest.mark.asyncio
    async def test_details_raises_graphql_error_on_http_400(self) -> None:
        """A response with a top-level `errors` array raises `GraphQLError` on 400."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {"errors": [{"message": "Metric not found"}]}
        response.raise_for_status = MagicMock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="Metric not found") as exc_info:
            await ops.details(999999)

        assert exc_info.value.status_code == 400
        response.raise_for_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_details_notes_and_dates(self) -> None:
        """`details()` extracts notes and returns a UTC-aware `created_date`."""
        client = AsyncMock()
        ops = AsyncMetricOperations(client, GRAPHQL_URL)
        node = {
            **METRIC_NODE,
            "notesId": "pad-1",
            "notesText": "Metric notes",
            "collaborationEnabled": True,
        }
        client.post.return_value = _async_response({"data": {"metric": node}})

        result = await ops.details(2036155)

        assert result.notes == "Metric notes"
        assert result.notes_id == "pad-1"
        assert result.created_date.tzinfo is not None
