"""Adversarial tests for Todos and Goals operations.

These tests target edge cases and known bugs in the todos and goals
operations, transforms, and bulk processing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, PropertyMock, patch

import pytest

from bloomy.operations.goals import GoalOperations
from bloomy.operations.mixins.goals_transform import GoalOperationsMixin
from bloomy.operations.mixins.todos_transform import TodoOperationsMixin
from bloomy.operations.todos import TodoOperations

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_http_client() -> Mock:
    """Create a mock HTTP client with default successful responses.

    Returns:
        A mock HTTP client.

    """
    client = Mock()
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {}
    client.get = Mock(return_value=response)
    client.post = Mock(return_value=response)
    client.put = Mock(return_value=response)
    client.delete = Mock(return_value=response)
    return client


@pytest.fixture
def mock_user_id() -> PropertyMock:
    """Mock user_id property returning 123.

    Yields:
        A PropertyMock that returns user ID 123.

    """
    with patch(
        "bloomy.utils.base_operations.BaseOperations.user_id",
        new_callable=PropertyMock,
    ) as mock:
        mock.return_value = 123
        yield mock


# ---------------------------------------------------------------------------
# Goal update() — accountable_user always defaults to self.user_id
# ---------------------------------------------------------------------------


class TestGoalUpdateOverwritesOwner:
    """Goal.update() should only send accountableUserId when explicitly provided.

    Previously, accountableUserId always defaulted to self.user_id, silently
    overwriting the goal owner. This has been fixed.
    """

    @pytest.fixture(autouse=True)
    def _setup_goal_get_response(self, mock_http_client: Mock) -> None:
        """Configure GET to return a valid goal response for the details() re-fetch."""
        get_response = Mock()
        get_response.raise_for_status = Mock()
        get_response.json.return_value = {
            "Id": 1,
            "Owner": {"Id": 123, "Name": "Alice"},
            "Name": "Goal Title",
            "CreateTime": "2024-01-01T00:00:00Z",
            "DueDate": "2024-12-31",
            "Complete": False,
            "Origins": [{"Id": 100, "Name": "Meeting A"}],
        }
        mock_http_client.get.return_value = get_response

    def test_update_title_only_should_not_overwrite_owner(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Updating only the title should NOT send accountableUserId."""
        goal_ops = GoalOperations(mock_http_client)
        goal_ops.update(goal_id=1, title="New Title")

        call_args = mock_http_client.put.call_args
        payload = call_args.kwargs.get("json") or call_args[1]["json"]

        assert "accountableUserId" not in payload, (
            "accountableUserId should not be in payload when not explicitly provided"
        )

    def test_update_status_only_should_not_overwrite_owner(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Updating only the status should NOT send accountableUserId."""
        goal_ops = GoalOperations(mock_http_client)
        goal_ops.update(goal_id=1, status="on")

        call_args = mock_http_client.put.call_args
        payload = call_args.kwargs.get("json") or call_args[1]["json"]

        assert "accountableUserId" not in payload, (
            "accountableUserId should not be in payload when not explicitly provided"
        )

    def test_update_with_explicit_accountable_user(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """When accountable_user is explicitly provided, it should be used."""
        goal_ops = GoalOperations(mock_http_client)
        goal_ops.update(goal_id=1, title="X", accountable_user=456)

        call_args = mock_http_client.put.call_args
        payload = call_args.kwargs.get("json") or call_args[1]["json"]

        assert payload["accountableUserId"] == 456


# ---------------------------------------------------------------------------
# _transform_goal_list — Origins edge cases
# ---------------------------------------------------------------------------


class TestGoalTransformOrigins:
    """Edge cases in _transform_goal_list around the Origins field."""

    def _make_goal(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "Id": 1,
            "Owner": {"Id": 10, "Name": "Alice"},
            "Name": "Goal A",
            "CreateTime": "2024-01-01T00:00:00Z",
            "DueDate": "2024-12-31",
            "Complete": False,
            "Origins": [{"Id": 100, "Name": "Meeting A"}],
        }
        base.update(overrides)
        return base

    def test_origins_empty_list(self) -> None:
        """Empty Origins list should yield meeting_id=None."""
        mixin = GoalOperationsMixin()
        goal = self._make_goal(Origins=[])
        result = mixin._transform_goal_list([goal])
        assert result[0].meeting_id is None
        assert result[0].meeting_title is None

    def test_origins_none(self) -> None:
        """Origins=None should yield meeting_id=None."""
        mixin = GoalOperationsMixin()
        goal = self._make_goal(Origins=None)
        result = mixin._transform_goal_list([goal])
        assert result[0].meeting_id is None
        assert result[0].meeting_title is None

    def test_origins_missing_key(self) -> None:
        """No Origins key at all should yield meeting_id=None."""
        mixin = GoalOperationsMixin()
        goal = self._make_goal()
        del goal["Origins"]
        result = mixin._transform_goal_list([goal])
        assert result[0].meeting_id is None

    def test_origins_with_none_element(self) -> None:
        """Origins=[None] is truthy but the element is None — should return None."""
        mixin = GoalOperationsMixin()
        goal = self._make_goal(Origins=[None])

        result = mixin._transform_goal_list([goal])
        assert result[0].meeting_id is None
        assert result[0].meeting_title is None

    def test_origins_with_empty_dict(self) -> None:
        """Origins=[{}] — empty dict is falsy, should return None."""
        mixin = GoalOperationsMixin()
        goal = self._make_goal(Origins=[{}])

        result = mixin._transform_goal_list([goal])
        assert result[0].meeting_id is None
        assert result[0].meeting_title is None


# ---------------------------------------------------------------------------
# _transform_created_goal — Origins not guarded
# ---------------------------------------------------------------------------


class TestCreatedGoalTransformOrigins:
    """_transform_created_goal unconditionally accesses Origins[0]."""

    def _make_create_response(self, **overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "Id": 999,
            "Owner": {"Id": 10, "Name": "Alice"},
            "Origins": [{"Id": 100, "Name": "Meeting A"}],
            "CreateTime": "2024-06-01T10:00:00Z",
            "Completion": 0,
        }
        base.update(overrides)
        return base

    def test_created_goal_empty_origins(self) -> None:
        """Empty Origins list should return meeting_title=None."""
        mixin = GoalOperationsMixin()
        data = self._make_create_response(Origins=[])

        result = mixin._transform_created_goal(data, "Goal", meeting_id=100, user_id=10)
        assert result.meeting_title is None

    def test_created_goal_origins_none(self) -> None:
        """Origins=None should return meeting_title=None."""
        mixin = GoalOperationsMixin()
        data = self._make_create_response(Origins=None)

        result = mixin._transform_created_goal(data, "Goal", meeting_id=100, user_id=10)
        assert result.meeting_title is None

    def test_created_goal_missing_origins_key(self) -> None:
        """Missing Origins key should return meeting_title=None."""
        mixin = GoalOperationsMixin()
        data = self._make_create_response()
        del data["Origins"]

        result = mixin._transform_created_goal(data, "Goal", meeting_id=100, user_id=10)
        assert result.meeting_title is None

    def test_created_goal_happy_path(self) -> None:
        """Normal case still works."""
        mixin = GoalOperationsMixin()
        data = self._make_create_response()
        result = mixin._transform_created_goal(
            data, "Goal X", meeting_id=100, user_id=10
        )

        assert result.id == 999
        assert result.title == "Goal X"
        assert result.meeting_title == "Meeting A"
        assert result.status == "off"

    def test_created_goal_completion_values(self) -> None:
        """Test all completion status mappings."""
        mixin = GoalOperationsMixin()

        for completion_val, expected_status in [(0, "off"), (1, "on"), (2, "complete")]:
            data = self._make_create_response(Completion=completion_val)
            result = mixin._transform_created_goal(data, "G", meeting_id=1, user_id=1)
            assert result.status == expected_status, (
                f"Completion={completion_val} should map to '{expected_status}'"
            )

    def test_created_goal_unknown_completion(self) -> None:
        """Unknown Completion value should default to 'off'."""
        mixin = GoalOperationsMixin()
        data = self._make_create_response(Completion=99)
        result = mixin._transform_created_goal(data, "G", meeting_id=1, user_id=1)
        assert result.status == "off"


# ---------------------------------------------------------------------------
# Todo create() — hardcoded response fields & datetime.now() fallback
# ---------------------------------------------------------------------------


class TestTodoCreateEdgeCases:
    """Tests for edge cases in todo creation response handling."""

    def test_create_response_missing_id_raises_keyerror(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """If API returns response without 'Id', KeyError is raised.

        This documents that the API contract requires the 'Id' field.
        """
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"Name": "Todo", "SomeOtherField": 123}
        mock_http_client.post.return_value = response

        todo_ops = TodoOperations(mock_http_client)

        with pytest.raises(KeyError, match="Id"):
            todo_ops.create(title="Test", meeting_id=1)

    def test_create_response_missing_name_raises_keyerror(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """BUG: If API returns response without 'Name', KeyError is raised."""
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"Id": 1, "Title": "Todo"}
        mock_http_client.post.return_value = response

        todo_ops = TodoOperations(mock_http_client)

        with pytest.raises(KeyError, match="Name"):
            todo_ops.create(title="Test", meeting_id=1)

    def test_create_response_minimal_fields(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Minimal API response with only Id and Name should succeed."""
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"Id": 42, "Name": "Minimal Todo"}
        mock_http_client.post.return_value = response

        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.create(title="Minimal Todo", meeting_id=1)

        assert result.id == 42
        assert result.name == "Minimal Todo"
        assert result.meeting_id == 1
        assert result.complete is False

    def test_create_datetime_fallback_is_utc(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """When CreateTime is missing, the fallback uses datetime.now(UTC)."""
        response = Mock()
        response.raise_for_status = Mock()
        # No CreateTime in the response
        response.json.return_value = {"Id": 1, "Name": "Todo"}
        mock_http_client.post.return_value = response

        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.create(title="Todo")

        assert result.create_date is not None
        assert result.create_date.tzinfo is not None, (
            "datetime fallback should be timezone-aware (UTC)"
        )

    def test_create_user_todo_payload(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """User todos (no meeting_id) use different payload and endpoint."""
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"Id": 1, "Name": "User Todo"}
        mock_http_client.post.return_value = response

        todo_ops = TodoOperations(mock_http_client)
        todo_ops.create(title="User Todo", due_date="2024-12-31", notes="Note")

        mock_http_client.post.assert_called_once_with(
            "todo/create",
            json={
                "title": "User Todo",
                "accountableUserId": 123,
                "notes": "Note",
                "dueDate": "2024-12-31",
            },
        )

    def test_create_meeting_todo_sets_origin_id(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Meeting todo should have meeting_id set from the input, not the response."""
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {"Id": 1, "Name": "Meeting Todo"}
        mock_http_client.post.return_value = response

        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.create(title="Meeting Todo", meeting_id=999)

        assert result.meeting_id == 999


# ---------------------------------------------------------------------------
# TodoOperationsMixin payload builders
# ---------------------------------------------------------------------------


class TestTodoPayloadBuilders:
    """Test the mixin payload builder methods for edge cases."""

    def test_meeting_todo_payload_minimal(self) -> None:
        """Build meeting todo payload with minimal fields."""
        mixin = TodoOperationsMixin()
        payload = mixin._build_meeting_todo_payload("Title", user_id=1)
        assert payload == {"Title": "Title", "ForId": 1}

    def test_meeting_todo_payload_full(self) -> None:
        """Build meeting todo payload with all fields."""
        mixin = TodoOperationsMixin()
        payload = mixin._build_meeting_todo_payload(
            "Title", user_id=1, notes="N", due_date="2024-01-01"
        )
        assert payload == {
            "Title": "Title",
            "ForId": 1,
            "Notes": "N",
            "dueDate": "2024-01-01",
        }

    def test_user_todo_payload_minimal(self) -> None:
        """Build user todo payload with minimal fields."""
        mixin = TodoOperationsMixin()
        payload = mixin._build_user_todo_payload("Title", user_id=1)
        assert payload == {"title": "Title", "accountableUserId": 1}

    def test_user_todo_payload_full(self) -> None:
        """Build user todo payload with all fields."""
        mixin = TodoOperationsMixin()
        payload = mixin._build_user_todo_payload(
            "Title", user_id=1, notes="N", due_date="2024-01-01"
        )
        assert payload == {
            "title": "Title",
            "accountableUserId": 1,
            "notes": "N",
            "dueDate": "2024-01-01",
        }

    def test_meeting_payload_inconsistent_casing(self) -> None:
        """Meeting todo payload uses mixed casing.

        PascalCase for Title/ForId/Notes but camelCase for dueDate.
        This test documents the inconsistency.
        """
        mixin = TodoOperationsMixin()
        payload = mixin._build_meeting_todo_payload(
            "T", user_id=1, notes="N", due_date="2024-01-01"
        )
        # PascalCase keys
        assert "Title" in payload
        assert "ForId" in payload
        assert "Notes" in payload
        # camelCase key — inconsistent
        assert "dueDate" in payload


# ---------------------------------------------------------------------------
# Goal _build_goal_update_payload edge cases
# ---------------------------------------------------------------------------


class TestGoalUpdatePayload:
    """Test _build_goal_update_payload for edge cases."""

    def test_payload_with_no_optional_fields(self) -> None:
        """Payload with only accountable_user."""
        mixin = GoalOperationsMixin()
        payload = mixin._build_goal_update_payload(accountable_user=42)
        assert payload == {"accountableUserId": 42}

    def test_payload_without_accountable_user(self) -> None:
        """Payload without accountable_user should not include it."""
        mixin = GoalOperationsMixin()
        payload = mixin._build_goal_update_payload(title="Updated")
        assert "accountableUserId" not in payload
        assert payload == {"title": "Updated"}

    def test_payload_with_goal_status_enum(self) -> None:
        """Test using GoalStatus enum values."""
        from bloomy.models import GoalStatus

        mixin = GoalOperationsMixin()

        for status, expected in [
            (GoalStatus.ON_TRACK, "OnTrack"),
            (GoalStatus.AT_RISK, "AtRisk"),
            (GoalStatus.COMPLETE, "Complete"),
        ]:
            payload = mixin._build_goal_update_payload(
                accountable_user=1, status=status
            )
            assert payload["completion"] == expected

    def test_payload_invalid_status_string(self) -> None:
        """Invalid status string should raise ValueError."""
        mixin = GoalOperationsMixin()
        with pytest.raises(ValueError, match="Invalid status value"):
            mixin._build_goal_update_payload(accountable_user=1, status="invalid")

    def test_payload_status_case_sensitivity(self) -> None:
        """Status strings are lowercased, so mixed case should work."""
        mixin = GoalOperationsMixin()
        payload = mixin._build_goal_update_payload(accountable_user=1, status="On")
        assert payload["completion"] == "OnTrack"

    def test_payload_status_complete_uppercase(self) -> None:
        """Uppercase COMPLETE should map to Complete."""
        mixin = GoalOperationsMixin()
        payload = mixin._build_goal_update_payload(
            accountable_user=1, status="COMPLETE"
        )
        assert payload["completion"] == "Complete"


# ---------------------------------------------------------------------------
# Bulk operations — mix of valid and invalid data
# ---------------------------------------------------------------------------


class TestBulkGoalCreation:
    """Test create_many with edge case inputs."""

    def test_bulk_create_missing_required_field(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Items missing 'title' should fail validation."""
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.create_many([{"meeting_id": 123}])

        assert len(result.successful) == 0
        assert len(result.failed) == 1
        assert "title" in result.failed[0].error.lower()

    def test_bulk_create_missing_meeting_id(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Items missing 'meeting_id' should fail validation."""
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.create_many([{"title": "Goal"}])

        assert len(result.successful) == 0
        assert len(result.failed) == 1
        assert "meeting_id" in result.failed[0].error.lower()

    def test_bulk_create_mix_valid_and_invalid(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Mix of valid and invalid items — valid ones should succeed."""
        create_response = Mock()
        create_response.raise_for_status = Mock()
        create_response.json.return_value = {
            "Id": 1,
            "Owner": {"Id": 123, "Name": "Me"},
            "Origins": [{"Id": 100, "Name": "Meeting"}],
            "CreateTime": "2024-01-01T00:00:00Z",
            "Completion": 0,
        }
        mock_http_client.post.return_value = create_response

        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.create_many(
            [
                {"title": "Valid Goal", "meeting_id": 100},
                {"meeting_id": 100},  # missing title
                {"title": "Another Valid", "meeting_id": 100},
            ]
        )

        assert len(result.successful) == 2
        assert len(result.failed) == 1
        assert result.failed[0].index == 1

    def test_bulk_create_empty_list(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Empty input should return empty results."""
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.create_many([])

        assert len(result.successful) == 0
        assert len(result.failed) == 0

    def test_bulk_create_all_invalid(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """All invalid items should all be in failed list."""
        goal_ops = GoalOperations(mock_http_client)
        result = goal_ops.create_many(
            [
                {"not_title": "X"},
                {"meeting_id": None, "title": None},
            ]
        )

        assert len(result.successful) == 0
        assert len(result.failed) == 2


class TestBulkTodoCreation:
    """Test todo create_many with edge case inputs."""

    def test_bulk_todo_missing_title(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Items missing 'title' should fail validation."""
        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.create_many([{"meeting_id": 1}])

        assert len(result.successful) == 0
        assert len(result.failed) == 1

    def test_bulk_todo_missing_meeting_id(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """Items missing 'meeting_id' should fail validation."""
        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.create_many([{"title": "Todo"}])

        assert len(result.successful) == 0
        assert len(result.failed) == 1

    def test_bulk_todo_api_error_captured(
        self, mock_http_client: Mock, mock_user_id: PropertyMock
    ) -> None:
        """API errors during creation should be captured, not raised."""
        error_response = Mock()
        error_response.raise_for_status.side_effect = Exception("API Error 500")
        mock_http_client.post.return_value = error_response

        todo_ops = TodoOperations(mock_http_client)
        result = todo_ops.create_many(
            [
                {"title": "Todo 1", "meeting_id": 1},
            ]
        )

        assert len(result.successful) == 0
        assert len(result.failed) == 1
        assert "API Error 500" in result.failed[0].error


# ---------------------------------------------------------------------------
# _transform_archived_goals edge cases
# ---------------------------------------------------------------------------


class TestArchivedGoalTransform:
    """Edge cases for _transform_archived_goals."""

    def test_empty_list(self) -> None:
        """Empty input should return empty list."""
        mixin = GoalOperationsMixin()
        result = mixin._transform_archived_goals([])
        assert result == []

    def test_missing_complete_field(self) -> None:
        """Goal without 'Complete' field should default to 'Incomplete'."""
        mixin = GoalOperationsMixin()
        data = [
            {
                "Id": 1,
                "Name": "Goal",
                "CreateTime": "2024-01-01T00:00:00Z",
                "DueDate": "2024-12-31",
            }
        ]
        result = mixin._transform_archived_goals(data)
        assert result[0].status == "Incomplete"

    def test_complete_true(self) -> None:
        """Complete=True should map to 'Complete' status."""
        mixin = GoalOperationsMixin()
        data = [
            {
                "Id": 1,
                "Name": "Goal",
                "CreateTime": "2024-01-01T00:00:00Z",
                "DueDate": "2024-12-31",
                "Complete": True,
            }
        ]
        result = mixin._transform_archived_goals(data)
        assert result[0].status == "Complete"

    def test_missing_due_date(self) -> None:
        """Goal with DueDate=None."""
        mixin = GoalOperationsMixin()
        data = [
            {
                "Id": 1,
                "Name": "Goal",
                "CreateTime": "2024-01-01T00:00:00Z",
                "DueDate": None,
            }
        ]
        result = mixin._transform_archived_goals(data)
        assert result[0].due_date is None
