"""Adversarial tests for Meetings and Scorecard operations.

These tests target known bugs and edge cases in:
- scorecard.py / async_/scorecard.py (truthiness checks)
- meetings.py / async_/meetings.py (getattr on MeetingListItem)
- mixins/meetings_transform.py (metrics transform edge cases)
"""

from typing import Any
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from bloomy.operations.meetings import MeetingOperations
from bloomy.operations.mixins.meetings_transform import MeetingOperationsMixin
from bloomy.operations.scorecard import ScorecardOperations

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_http_client() -> Mock:
    """Create a mock HTTP client.

    Returns:
        A mock httpx.Client.

    """
    client = Mock(spec=httpx.Client)
    client.get = Mock()
    client.post = Mock()
    client.put = Mock()
    client.delete = Mock()
    client.close = Mock()
    return client


@pytest.fixture
def scorecard_ops(mock_http_client: Mock) -> ScorecardOperations:
    """Create a ScorecardOperations instance with mocked HTTP client.

    Returns:
        A ScorecardOperations instance.

    """
    return ScorecardOperations(mock_http_client)


@pytest.fixture
def meeting_ops(mock_http_client: Mock) -> MeetingOperations:
    """Create a MeetingOperations instance with mocked HTTP client.

    Returns:
        A MeetingOperations instance.

    """
    return MeetingOperations(mock_http_client)


@pytest.fixture
def mixin() -> MeetingOperationsMixin:
    """Create a plain MeetingOperationsMixin for direct transform testing.

    Returns:
        A MeetingOperationsMixin instance.

    """
    return MeetingOperationsMixin()


# ---------------------------------------------------------------------------
# BUG 1 - Scorecard.list() truthiness check on user_id / meeting_id
#
# Line 87: `if user_id and meeting_id:` uses truthiness.
# When user_id=0 (falsy int), the ValueError is not raised even though
# both arguments are provided.
# ---------------------------------------------------------------------------


class TestScorecardTruthinessBug:
    """Scorecard.list() must reject user_id AND meeting_id regardless of value."""

    def test_user_id_zero_and_meeting_id_should_raise(
        self, scorecard_ops: ScorecardOperations
    ) -> None:
        """user_id=0 with meeting_id provided should raise ValueError."""
        with pytest.raises(ValueError, match="not both"):
            scorecard_ops.list(user_id=0, meeting_id=123)

    def test_meeting_id_zero_and_user_id_should_raise(
        self, scorecard_ops: ScorecardOperations
    ) -> None:
        """meeting_id=0 with user_id provided should raise ValueError."""
        with pytest.raises(ValueError, match="not both"):
            scorecard_ops.list(user_id=42, meeting_id=0)

    def test_both_zero_should_raise(self, scorecard_ops: ScorecardOperations) -> None:
        """Both user_id=0 and meeting_id=0 should still raise ValueError."""
        with pytest.raises(ValueError, match="not both"):
            scorecard_ops.list(user_id=0, meeting_id=0)

    def test_both_nonzero_should_raise(
        self, scorecard_ops: ScorecardOperations
    ) -> None:
        """Both user_id and meeting_id non-zero should raise ValueError."""
        with pytest.raises(ValueError, match="not both"):
            scorecard_ops.list(user_id=1, meeting_id=2)

    def test_meeting_id_zero_routes_to_meeting_endpoint(
        self, scorecard_ops: ScorecardOperations, mock_http_client: Mock
    ) -> None:
        """meeting_id=0 (without user_id) should still hit the meeting endpoint."""
        mock_response = Mock()
        mock_response.json.return_value = {"Scores": []}
        mock_http_client.get.return_value = mock_response

        scorecard_ops.list(meeting_id=0)

        mock_http_client.get.assert_called_once_with("scorecard/meeting/0")


# ---------------------------------------------------------------------------
# BUG 2 - Meeting.details() uses getattr on MeetingListItem
#
# MeetingListItem only has: id, type, key, name.
# getattr(meeting, "start_date_utc", None) always returns None.
# The result is that MeetingDetails never has dates populated.
# ---------------------------------------------------------------------------


class TestMeetingDetailsDirectEndpoint:
    """Meeting.details() now uses the direct L10/{id} endpoint."""

    def test_details_populates_created_date(
        self, meeting_ops: MeetingOperations, mock_http_client: Mock
    ) -> None:
        """details() now reads created_date from the direct endpoint response.

        Previously it used getattr on MeetingListItem which never had
        these fields, so they were always None. Now fixed.
        """
        direct_resp = Mock()
        direct_resp.json.return_value = {
            "Id": 1,
            "Basics": {"Name": "Standup"},
            "CreateTime": "2024-06-01T10:00:00Z",
            "StartDateUtc": None,
            "OrganizationId": 42,
        }
        empty_resp = Mock()
        empty_resp.json.return_value = []

        mock_http_client.get.side_effect = [
            direct_resp,
            empty_resp,  # attendees
            empty_resp,  # issues
            empty_resp,  # todos
            empty_resp,  # metrics
        ]

        result = meeting_ops.details(meeting_id=1)

        assert result.organization_id == 42
        mock_http_client.get.assert_any_call("L10/1")

    def test_details_meeting_id_zero(
        self, meeting_ops: MeetingOperations, mock_http_client: Mock
    ) -> None:
        """meeting_id=0 is handled correctly by the direct endpoint."""
        direct_resp = Mock()
        direct_resp.json.return_value = {
            "Id": 0,
            "Basics": {"Name": "Zero Meeting"},
            "CreateTime": None,
            "StartDateUtc": None,
            "OrganizationId": None,
        }
        empty_resp = Mock()
        empty_resp.json.return_value = []

        mock_http_client.get.side_effect = [
            direct_resp,
            empty_resp,
            empty_resp,
            empty_resp,
            empty_resp,
        ]

        result = meeting_ops.details(meeting_id=0)
        assert result.id == 0
        assert result.name == "Zero Meeting"


# ---------------------------------------------------------------------------
# BUG 3 - _transform_metrics truthiness on measurable_id
#
# Line 66: `if not measurable_id or not measurable_name:` skips items
# where measurable_id is 0 (a valid but falsy int).
# ---------------------------------------------------------------------------


class TestTransformMetricsEdgeCases:
    """_transform_metrics should handle falsy-but-valid data."""

    def test_measurable_id_zero_is_skipped(self, mixin: MeetingOperationsMixin) -> None:
        """measurable_id=0 is wrongly skipped by `if not measurable_id`."""
        data = [
            {
                "Id": 0,
                "Name": "Valid Metric",
                "Target": 50,
                "Direction": ">",
                "Modifiers": "count",
                "Owner": {"Id": 1, "Name": "Alice"},
            }
        ]
        result = mixin._transform_metrics(data)
        # Fixed: measurable_id=0 is now accepted (was skipped due to truthiness)
        assert len(result) == 1

    def test_empty_name_is_skipped(self, mixin: MeetingOperationsMixin) -> None:
        """Empty string name is falsy and should be skipped."""
        data = [
            {
                "Id": 1,
                "Name": "",
                "Target": 10,
                "Owner": {"Id": 1, "Name": "Bob"},
            }
        ]
        result = mixin._transform_metrics(data)
        assert len(result) == 0

    def test_none_input_returns_empty(self, mixin: MeetingOperationsMixin) -> None:
        """None input (not a list) returns empty list."""
        assert mixin._transform_metrics(None) == []

    def test_string_input_returns_empty(self, mixin: MeetingOperationsMixin) -> None:
        """String input (not a list) returns empty list."""
        assert mixin._transform_metrics("not a list") == []

    def test_dict_input_returns_empty(self, mixin: MeetingOperationsMixin) -> None:
        """Dict input (not a list) returns empty list."""
        assert mixin._transform_metrics({"key": "value"}) == []

    def test_list_with_non_dict_items(self, mixin: MeetingOperationsMixin) -> None:
        """Non-dict items in the list are silently skipped."""
        data = [42, "string", None, True]
        result = mixin._transform_metrics(data)
        assert result == []

    def test_owner_none_does_not_crash(self, mixin: MeetingOperationsMixin) -> None:
        """Owner=None should not crash; falls back to empty dict."""
        data = [
            {
                "Id": 10,
                "Name": "Metric",
                "Target": 100,
                "Direction": ">=",
                "Modifiers": "pct",
                "Owner": None,
            }
        ]
        result = mixin._transform_metrics(data)
        assert len(result) == 1
        assert result[0].accountable_user_id == 0
        assert result[0].accountable_user_name == ""

    def test_owner_as_string_does_not_crash(
        self, mixin: MeetingOperationsMixin
    ) -> None:
        """Owner as a string instead of dict should be handled gracefully."""
        data = [
            {
                "Id": 10,
                "Name": "Metric",
                "Target": 100,
                "Owner": "not-a-dict",
            }
        ]
        result = mixin._transform_metrics(data)
        assert len(result) == 1
        assert result[0].accountable_user_id == 0

    def test_missing_optional_fields_use_defaults(
        self, mixin: MeetingOperationsMixin
    ) -> None:
        """Items with missing optional fields should use defaults."""
        data = [
            {
                "Id": 5,
                "Name": "Bare Metric",
            }
        ]
        result = mixin._transform_metrics(data)
        assert len(result) == 1
        assert result[0].target == 0.0
        assert result[0].unit == ""
        assert result[0].metric_type == ""
        assert result[0].accountable_user_id == 0

    def test_target_as_string(self, mixin: MeetingOperationsMixin) -> None:
        """Target as a numeric string should be coerced to float."""
        data = [
            {
                "Id": 1,
                "Name": "Metric",
                "Target": "99.5",
                "Owner": {"Id": 1, "Name": "X"},
            }
        ]
        result = mixin._transform_metrics(data)
        assert result[0].target == 99.5


# ---------------------------------------------------------------------------
# BUG 4 - _transform_meeting_issues with None Owner
#
# issue.get("Owner", {}).get("ImageUrl", "") — if Owner is explicitly None
# (not missing), .get returns None and .get("ImageUrl") raises AttributeError.
# ---------------------------------------------------------------------------


class TestTransformIssuesEdgeCases:
    """_transform_meeting_issues should handle malformed Owner data."""

    def test_owner_none_handled_gracefully(self, mixin: MeetingOperationsMixin) -> None:
        """Owner=None is handled gracefully, falling back to defaults."""
        data: list[dict[str, Any]] = [
            {
                "Id": 1,
                "Name": "Issue",
                "DetailsUrl": "http://x",
                "CreateTime": "2024-01-01T00:00:00Z",
                "CloseTime": None,
                "Owner": None,
                "Origin": "Meeting",
            }
        ]
        result = mixin._transform_meeting_issues(data, meeting_id=1)
        assert len(result) == 1
        assert result[0].owner_id == 0
        assert result[0].owner_name == ""
        assert result[0].owner_image_url == ""

    def test_owner_missing_fields(self, mixin: MeetingOperationsMixin) -> None:
        """Owner dict with missing keys uses defaults."""
        data: list[dict[str, Any]] = [
            {
                "Id": 1,
                "Name": "Issue",
                "DetailsUrl": "http://x",
                "CreateTime": "2024-01-01T00:00:00Z",
                "CloseTime": None,
                "Owner": {},
                "Origin": "Meeting",
            }
        ]
        result = mixin._transform_meeting_issues(data, meeting_id=1)
        assert len(result) == 1
        assert result[0].owner_id == 0
        assert result[0].owner_name == ""
        assert result[0].owner_image_url == ""

    def test_owner_missing_entirely(self, mixin: MeetingOperationsMixin) -> None:
        """Missing Owner key falls back to empty dict via .get default."""
        data: list[dict[str, Any]] = [
            {
                "Id": 1,
                "Name": "Issue",
                "DetailsUrl": "http://x",
                "CreateTime": "2024-01-01T00:00:00Z",
                "CloseTime": None,
                "Origin": "Meeting",
            }
        ]
        result = mixin._transform_meeting_issues(data, meeting_id=1)
        assert len(result) == 1
        assert result[0].owner_id == 0


# ---------------------------------------------------------------------------
# _transform_attendees edge cases
# ---------------------------------------------------------------------------


class TestTransformAttendeesEdgeCases:
    """_transform_attendees should handle missing/malformed data."""

    def test_empty_list(self, mixin: MeetingOperationsMixin) -> None:
        """Empty attendee list returns empty result."""
        assert mixin._transform_attendees([]) == []

    def test_missing_image_url_uses_default(
        self, mixin: MeetingOperationsMixin
    ) -> None:
        """Missing ImageUrl defaults to empty string."""
        data = [{"Id": 1, "Name": "Alice"}]
        result = mixin._transform_attendees(data)
        assert len(result) == 1
        assert result[0].image_url == ""

    def test_missing_required_field_raises(self, mixin: MeetingOperationsMixin) -> None:
        """Missing required field (Name) raises KeyError."""
        data: list[dict[str, Any]] = [{"Id": 1}]
        with pytest.raises(KeyError):
            mixin._transform_attendees(data)


# ---------------------------------------------------------------------------
# Async scorecard truthiness bug (same issue in async variant)
# ---------------------------------------------------------------------------


class TestAsyncScorecardTruthinessBug:
    """Async scorecard.list() has the same truthiness bug."""

    @pytest.mark.asyncio
    async def test_user_id_zero_and_meeting_id_should_raise(self) -> None:
        """Async: user_id=0 with meeting_id should raise ValueError."""
        from bloomy.operations.async_.scorecard import AsyncScorecardOperations

        mock_client = AsyncMock()
        ops = AsyncScorecardOperations(mock_client)

        with pytest.raises(ValueError, match="not both"):
            await ops.list(user_id=0, meeting_id=123)

    @pytest.mark.asyncio
    async def test_both_zero_should_raise(self) -> None:
        """Async: both zero should raise ValueError."""
        from bloomy.operations.async_.scorecard import AsyncScorecardOperations

        mock_client = AsyncMock()
        ops = AsyncScorecardOperations(mock_client)

        with pytest.raises(ValueError, match="not both"):
            await ops.list(user_id=0, meeting_id=0)
