"""Tests for the v2 (GraphQL) milestone operations."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from bloomy.exceptions import GraphQLError
from bloomy.v2.base import MILESTONES_CONNECTION
from bloomy.v2.models import Milestone
from bloomy.v2.operations.milestone import AsyncMilestoneOperations, MilestoneOperations

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


class TestMilestoneOperationsSync:
    """Tests for the sync `MilestoneOperations`."""

    def test_list(self) -> None:
        """`list()` returns milestones for a goal, via `goal(id){ milestones }`."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}
        )

        result = ops.list(5265048)

        assert len(result) == 1
        assert isinstance(result[0], Milestone)
        assert result[0].id == 6440354
        assert result[0].goal_id == 5265048
        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"goalId": 5265048}
        assert MILESTONES_CONNECTION in client.post.call_args.kwargs["json"]["query"]
        # Unix-seconds timestamps become UTC-aware datetimes.
        assert result[0].due_date.tzinfo is not None

    def test_list_with_null_goal_returns_empty(self) -> None:
        """A `null` `goal` (e.g. an unknown goal id) yields an empty list."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"goal": None}})

        result = ops.list(999999)

        assert result == []

    def test_list_raises_graphql_error_on_http_400_with_errors(self) -> None:
        """A body with a top-level `errors` array raises `GraphQLError` on HTTP 400."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        response = Mock()
        response.status_code = 400
        response.json.return_value = {"errors": [{"message": "Goal not found"}]}
        response.raise_for_status = Mock()
        client.post.return_value = response

        with pytest.raises(GraphQLError, match="Goal not found") as exc_info:
            ops.list(5265048)

        assert exc_info.value.status_code == 400
        response.raise_for_status.assert_not_called()

    def test_create(self) -> None:
        """`create()` sends `rockId` and re-reads the milestone via its goal."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateMilestone": {"id": 6440354}}}),
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
        ]

        result = ops.create(5265048, "SDK v2 test milestone", 1767225600)

        assert result.id == 6440354
        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables == {
            "input": {
                "rockId": 5265048,
                "title": "SDK v2 test milestone",
                "dueDate": 1767225600.0,
                "completed": False,
            }
        }

    def test_create_due_date_accepts_datetime_object(self) -> None:
        """`create(due_date=...)` accepts a `datetime`, not only a unix timestamp."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"CreateMilestone": {"id": 6440354}}}),
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
        ]
        due_date = datetime(2026, 1, 1, tzinfo=UTC)

        ops.create(5265048, "SDK v2 test milestone", due_date)

        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables["input"]["dueDate"] == due_date.timestamp()

    def test_create_raises_when_create_milestone_id_is_zero(self) -> None:
        """`create()` raises `GraphQLError` when `CreateMilestone` returns id `0`."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response({"data": {"CreateMilestone": {"id": 0}}})

        with pytest.raises(GraphQLError, match="create milestone failed"):
            ops.create(5265048, "SDK v2 test milestone", 1767225600)

        assert client.post.call_count == 1

    def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`, before any request."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            ops.update(6440354, goal_id=5265048)

        assert client.post.call_count == 0

    def test_update_due_date_and_completed(self) -> None:
        """`update(due_date=..., completed=...)` sends both without `title`."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            # Membership verification, before anything is written.
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
            _response({"data": {"EditMilestone": {"id": 6440354}}}),
            _response(
                {
                    "data": {
                        "goal": {
                            "milestones": {
                                "nodes": [
                                    {
                                        **MILESTONE_NODE,
                                        "dueDate": 1767312000,
                                        "completed": True,
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
        ]

        result = ops.update(
            6440354, goal_id=5265048, due_date=1767312000, completed=True
        )

        assert result.completed is True
        assert client.post.call_count == 3
        edit_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_variables == {
            "input": {
                "milestoneId": 6440354,
                "dueDate": 1767312000.0,
                "completed": True,
            }
        }

    def test_update(self) -> None:
        """`update()` verifies membership, sends only the given fields, and re-reads."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
            _response({"data": {"EditMilestone": {"id": 6440354}}}),
            _response(
                {
                    "data": {
                        "goal": {
                            "milestones": {
                                "nodes": [{**MILESTONE_NODE, "title": "Updated"}]
                            }
                        }
                    }
                }
            ),
        ]

        result = ops.update(6440354, goal_id=5265048, title="Updated")

        assert result.title == "Updated"
        verify_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert verify_variables == {"goalId": 5265048, "milestoneId": 6440354}
        edit_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_variables == {"input": {"milestoneId": 6440354, "title": "Updated"}}
        get_variables = client.post.call_args_list[2].kwargs["json"]["variables"]
        assert get_variables == {"goalId": 5265048, "milestoneId": 6440354}

    def test_update_wrong_goal_id_raises_without_writing(self) -> None:
        """A `goal_id` that does not own `milestone_id` raises before any write.

        The membership check runs before `EditMilestone`, so a wrong
        `goal_id` never sends the edit at all.
        """
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"goal": {"milestones": {"nodes": []}}}}
        )

        with pytest.raises(GraphQLError, match="Milestone 6440354 not found"):
            ops.update(6440354, goal_id=999999, title="Updated")

        assert client.post.call_count == 1

    def test_complete(self) -> None:
        """`complete()` verifies membership, then sends `completed: true`."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
            _response({"data": {"EditMilestone": {"id": 6440354}}}),
            _response(
                {
                    "data": {
                        "goal": {
                            "milestones": {
                                "nodes": [{**MILESTONE_NODE, "completed": True}]
                            }
                        }
                    }
                }
            ),
        ]

        result = ops.complete(6440354, goal_id=5265048)

        assert result.completed is True
        assert client.post.call_count == 3
        verify_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert verify_variables == {"goalId": 5265048, "milestoneId": 6440354}
        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {"milestoneId": 6440354, "completed": True}

    def test_update_raises_when_edit_milestone_returns_null(self) -> None:
        """A `null` `EditMilestone` result raises `GraphQLError` without a re-read."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
            _response({"data": {"EditMilestone": None}}),
        ]

        with pytest.raises(GraphQLError, match="update milestone failed"):
            ops.update(6440354, goal_id=5265048, title="Updated")

        assert client.post.call_count == 2

    def test_complete_wrong_goal_id_raises_without_writing(self) -> None:
        """A `goal_id` that does not own `milestone_id` raises before any write."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"goal": {"milestones": {"nodes": []}}}}
        )

        with pytest.raises(GraphQLError, match="Milestone 6440354 not found"):
            ops.complete(6440354, goal_id=999999)

        assert client.post.call_count == 1

    def test_get_raises_when_not_found(self) -> None:
        """If the milestone is gone by the final re-read, it raises.

        Edge case where the membership check passes but the milestone is
        removed before the final re-read (e.g. a concurrent delete).
        """
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _response({"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}),
            _response({"data": {"EditMilestone": {"id": 6440354}}}),
            _response({"data": {"goal": {"milestones": {"nodes": []}}}}),
        ]

        with pytest.raises(GraphQLError, match="not found"):
            ops.complete(6440354, goal_id=5265048)

    def test_delete(self) -> None:
        """`delete()` calls `DeleteMilestone` and checks its success result."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {"data": {"DeleteMilestone": {"success": True, "message": None}}}
        )

        ops.delete(6440354)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"milestoneId": 6440354}

    def test_delete_raises_on_failure(self) -> None:
        """`delete()` raises `GraphQLError` when `DeleteMilestone` reports failure."""
        client = Mock()
        ops = MilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _response(
            {
                "data": {
                    "DeleteMilestone": {
                        "success": False,
                        "message": "nope",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="nope"):
            ops.delete(6440354)


class TestMilestoneOperationsAsync:
    """Tests for the async `AsyncMilestoneOperations`."""

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """`list()` returns milestones for a goal."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}
        )

        result = await ops.list(5265048)

        assert len(result) == 1
        assert result[0].id == 6440354

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """`create()` sends `rockId` and re-reads the milestone via its goal."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response({"data": {"CreateMilestone": {"id": 6440354}}}),
            _async_response(
                {"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}
            ),
        ]

        result = await ops.create(5265048, "SDK v2 test milestone", 1767225600)

        assert result.id == 6440354
        create_variables = client.post.call_args_list[0].kwargs["json"]["variables"]
        assert create_variables == {
            "input": {
                "rockId": 5265048,
                "title": "SDK v2 test milestone",
                "dueDate": 1767225600.0,
                "completed": False,
            }
        }

    @pytest.mark.asyncio
    async def test_create_raises_when_create_milestone_id_is_zero(self) -> None:
        """`create()` raises `GraphQLError` when `CreateMilestone` returns id `0`."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"CreateMilestone": {"id": 0}}}
        )

        with pytest.raises(GraphQLError, match="create milestone failed"):
            await ops.create(5265048, "SDK v2 test milestone", 1767225600)

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_update_no_fields_raises(self) -> None:
        """`update()` with no fields raises `ValueError`, before any request."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)

        with pytest.raises(ValueError, match="At least one field"):
            await ops.update(6440354, goal_id=5265048)

        assert client.post.call_count == 0

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        """`update()` verifies membership, sends only the given fields, and re-reads."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}
            ),
            _async_response({"data": {"EditMilestone": {"id": 6440354}}}),
            _async_response(
                {
                    "data": {
                        "goal": {
                            "milestones": {
                                "nodes": [
                                    {
                                        **MILESTONE_NODE,
                                        "title": "Updated",
                                        "dueDate": 1767312000,
                                        "completed": True,
                                    }
                                ]
                            }
                        }
                    }
                }
            ),
        ]

        result = await ops.update(
            6440354,
            goal_id=5265048,
            title="Updated",
            due_date=1767312000,
            completed=True,
        )

        assert result.title == "Updated"
        assert result.completed is True
        assert client.post.call_count == 3
        edit_variables = client.post.call_args_list[1].kwargs["json"]["variables"]
        assert edit_variables == {
            "input": {
                "milestoneId": 6440354,
                "title": "Updated",
                "dueDate": 1767312000.0,
                "completed": True,
            }
        }

    @pytest.mark.asyncio
    async def test_update_wrong_goal_id_raises_without_writing(self) -> None:
        """A `goal_id` that does not own `milestone_id` raises before any write."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"goal": {"milestones": {"nodes": []}}}}
        )

        with pytest.raises(GraphQLError, match="not found"):
            await ops.update(6440354, goal_id=999999, title="Updated")

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_raises_when_not_found(self) -> None:
        """If the milestone is gone by the final re-read, it raises."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}
            ),
            _async_response({"data": {"EditMilestone": {"id": 6440354}}}),
            _async_response({"data": {"goal": {"milestones": {"nodes": []}}}}),
        ]

        with pytest.raises(GraphQLError, match="not found"):
            await ops.complete(6440354, goal_id=5265048)

    @pytest.mark.asyncio
    async def test_complete(self) -> None:
        """`complete()` verifies membership, sends `completed: true`, and re-reads."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.side_effect = [
            _async_response(
                {"data": {"goal": {"milestones": {"nodes": [MILESTONE_NODE]}}}}
            ),
            _async_response({"data": {"EditMilestone": {"id": 6440354}}}),
            _async_response(
                {
                    "data": {
                        "goal": {
                            "milestones": {
                                "nodes": [{**MILESTONE_NODE, "completed": True}]
                            }
                        }
                    }
                }
            ),
        ]

        result = await ops.complete(6440354, goal_id=5265048)

        assert result.completed is True
        assert client.post.call_count == 3
        edit_input = client.post.call_args_list[1].kwargs["json"]["variables"]["input"]
        assert edit_input == {"milestoneId": 6440354, "completed": True}

    @pytest.mark.asyncio
    async def test_complete_wrong_goal_id_raises_without_writing(self) -> None:
        """A `goal_id` that does not own `milestone_id` raises before any write."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"goal": {"milestones": {"nodes": []}}}}
        )

        with pytest.raises(GraphQLError, match="not found"):
            await ops.complete(6440354, goal_id=999999)

        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """`delete()` calls `DeleteMilestone` and checks its success result."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {"data": {"DeleteMilestone": {"success": True, "message": None}}}
        )

        await ops.delete(6440354)

        variables = client.post.call_args.kwargs["json"]["variables"]
        assert variables == {"milestoneId": 6440354}

    @pytest.mark.asyncio
    async def test_delete_raises_on_failure(self) -> None:
        """`delete()` raises `GraphQLError` when `DeleteMilestone` reports failure."""
        client = AsyncMock()
        ops = AsyncMilestoneOperations(client, GRAPHQL_URL)
        client.post.return_value = _async_response(
            {
                "data": {
                    "DeleteMilestone": {
                        "success": False,
                        "message": "nope",
                        "errorDetails": None,
                    }
                }
            }
        )

        with pytest.raises(GraphQLError, match="nope"):
            await ops.delete(6440354)
