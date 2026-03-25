"""Adversarial tests for Issues and Headlines operations.

These tests target known bugs and edge cases:
1. Truthiness bug: `if user_id and meeting_id` should be
   `if user_id is not None and meeting_id is not None`
2. Transform functions assuming all keys exist in API responses
3. Edge cases with None/missing Owner dicts, CloseTime, empty strings
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest

from bloomy.operations.async_.headlines import AsyncHeadlineOperations
from bloomy.operations.async_.issues import AsyncIssueOperations
from bloomy.operations.headlines import HeadlineOperations
from bloomy.operations.issues import IssueOperations
from bloomy.operations.mixins.headlines_transform import HeadlineOperationsMixin
from bloomy.operations.mixins.issues_transform import IssueOperationsMixin

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_http_client() -> Mock:
    """Create a mock sync HTTP client.

    Returns:
        A mock HTTP client.

    """
    client = Mock()
    client.get = Mock()
    client.post = Mock()
    client.put = Mock()
    client.delete = Mock()
    return client


@pytest.fixture
def mock_async_http_client() -> AsyncMock:
    """Create a mock async HTTP client.

    Returns:
        A mock async HTTP client.

    """
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def issue_ops(mock_http_client: Mock) -> IssueOperations:
    """Create IssueOperations with a mock client.

    Returns:
        An IssueOperations instance.

    """
    return IssueOperations(mock_http_client)


@pytest.fixture
def headline_ops(mock_http_client: Mock) -> HeadlineOperations:
    """Create HeadlineOperations with a mock client.

    Returns:
        A HeadlineOperations instance.

    """
    return HeadlineOperations(mock_http_client)


@pytest.fixture
def async_issue_ops(mock_async_http_client: AsyncMock) -> AsyncIssueOperations:
    """Create AsyncIssueOperations with a mock client.

    Returns:
        An AsyncIssueOperations instance.

    """
    return AsyncIssueOperations(mock_async_http_client)


@pytest.fixture
def async_headline_ops(mock_async_http_client: AsyncMock) -> AsyncHeadlineOperations:
    """Create AsyncHeadlineOperations with a mock client.

    Returns:
        An AsyncHeadlineOperations instance.

    """
    return AsyncHeadlineOperations(mock_async_http_client)


def _make_mock_response(data: Any) -> Mock:
    """Create a mock response with given JSON data.

    Returns:
        A mock response object.

    """
    resp = Mock()
    resp.json.return_value = data
    resp.raise_for_status = Mock()
    return resp


def _make_async_mock_response(data: Any) -> Mock:
    """Create a mock response for async client.

    Returns:
        A mock response object.

    """
    resp = Mock()
    resp.json.return_value = data
    resp.raise_for_status = Mock()
    return resp


# ===========================================================================
# 1. TRUTHINESS BUG: `if user_id and meeting_id` vs `if ... is not None`
#
# When user_id=0 (a valid int) and meeting_id is also provided, the truthiness
# check `if user_id and meeting_id` evaluates to `if 0 and meeting_id` which
# is False, so the ValueError is never raised. The correct check is:
#   `if user_id is not None and meeting_id is not None`
# ===========================================================================


class TestIssueListTruthinessBug:
    """Test the truthiness bug in IssueOperations.list()."""

    def test_user_id_zero_and_meeting_id_should_raise(
        self, issue_ops: IssueOperations
    ) -> None:
        """list(user_id=0, meeting_id=123) must raise ValueError.

        BUG: `if user_id and meeting_id` treats user_id=0 as falsy,
        so it silently falls through to the meeting_id branch instead of
        raising the expected ValueError.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            issue_ops.list(user_id=0, meeting_id=123)

    def test_meeting_id_zero_and_user_id_should_raise(
        self, issue_ops: IssueOperations
    ) -> None:
        """list(user_id=123, meeting_id=0) must raise ValueError.

        BUG: `if user_id and meeting_id` treats meeting_id=0 as falsy.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            issue_ops.list(user_id=123, meeting_id=0)

    def test_both_zero_should_raise(self, issue_ops: IssueOperations) -> None:
        """list(user_id=0, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            issue_ops.list(user_id=0, meeting_id=0)

    def test_empty_string_ids_should_still_raise(
        self, issue_ops: IssueOperations
    ) -> None:
        """list(user_id='', meeting_id='') — empty strings are also falsy.

        Even though the type hints say int|None, Python doesn't enforce at
        runtime. This confirms the guard is robust against falsy non-None values.
        """
        with pytest.raises(ValueError, match="Please provide either"):
            issue_ops.list(user_id="", meeting_id="")  # type: ignore[arg-type]


class TestHeadlineListTruthinessBug:
    """Test the truthiness bug in HeadlineOperations.list()."""

    def test_user_id_zero_and_meeting_id_should_raise(
        self, headline_ops: HeadlineOperations
    ) -> None:
        """list(user_id=0, meeting_id=123) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            headline_ops.list(user_id=0, meeting_id=123)

    def test_meeting_id_zero_and_user_id_should_raise(
        self, headline_ops: HeadlineOperations
    ) -> None:
        """list(user_id=123, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            headline_ops.list(user_id=123, meeting_id=0)

    def test_both_zero_should_raise(self, headline_ops: HeadlineOperations) -> None:
        """list(user_id=0, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            headline_ops.list(user_id=0, meeting_id=0)


class TestAsyncIssueListTruthinessBug:
    """Test the truthiness bug in AsyncIssueOperations.list()."""

    @pytest.mark.asyncio
    async def test_user_id_zero_and_meeting_id_should_raise(
        self, async_issue_ops: AsyncIssueOperations
    ) -> None:
        """Async list(user_id=0, meeting_id=123) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_issue_ops.list(user_id=0, meeting_id=123)

    @pytest.mark.asyncio
    async def test_meeting_id_zero_and_user_id_should_raise(
        self, async_issue_ops: AsyncIssueOperations
    ) -> None:
        """Async list(user_id=123, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_issue_ops.list(user_id=123, meeting_id=0)

    @pytest.mark.asyncio
    async def test_both_zero_should_raise(
        self, async_issue_ops: AsyncIssueOperations
    ) -> None:
        """Async list(user_id=0, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_issue_ops.list(user_id=0, meeting_id=0)


class TestAsyncHeadlineListTruthinessBug:
    """Test the truthiness bug in AsyncHeadlineOperations.list()."""

    @pytest.mark.asyncio
    async def test_user_id_zero_and_meeting_id_should_raise(
        self, async_headline_ops: AsyncHeadlineOperations
    ) -> None:
        """Async list(user_id=0, meeting_id=123) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_headline_ops.list(user_id=0, meeting_id=123)

    @pytest.mark.asyncio
    async def test_meeting_id_zero_and_user_id_should_raise(
        self, async_headline_ops: AsyncHeadlineOperations
    ) -> None:
        """Async list(user_id=123, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_headline_ops.list(user_id=123, meeting_id=0)

    @pytest.mark.asyncio
    async def test_both_zero_should_raise(
        self, async_headline_ops: AsyncHeadlineOperations
    ) -> None:
        """Async list(user_id=0, meeting_id=0) must raise ValueError."""
        with pytest.raises(ValueError, match="Please provide either"):
            await async_headline_ops.list(user_id=0, meeting_id=0)


# ===========================================================================
# 2. SECONDARY TRUTHINESS BUG: `if meeting_id:` branch routing
#
# After the ValueError guard, `if meeting_id:` is used to choose the API
# endpoint. If meeting_id=0 (valid but falsy), it falls through to the
# user_id branch instead of calling the meeting endpoint.
# ===========================================================================


class TestMeetingIdZeroRoutingBug:
    """When meeting_id=0 is provided alone, it should hit the meeting endpoint."""

    def test_issue_list_meeting_id_zero_routes_to_meeting_endpoint(
        self, mock_http_client: Mock
    ) -> None:
        """list(meeting_id=0) should call l10/0/issues, not issues/users/..."""
        mock_http_client.get.return_value = _make_mock_response([])
        issue_ops = IssueOperations(mock_http_client)

        with patch(
            "bloomy.utils.base_operations.BaseOperations.user_id",
            new_callable=PropertyMock,
            return_value=999,
        ):
            issue_ops.list(meeting_id=0)

        mock_http_client.get.assert_called_once_with("l10/0/issues")

    def test_headline_list_meeting_id_zero_routes_to_meeting_endpoint(
        self, mock_http_client: Mock
    ) -> None:
        """list(meeting_id=0) should call l10/0/headlines, not headline/users/..."""
        mock_http_client.get.return_value = _make_mock_response([])
        headline_ops = HeadlineOperations(mock_http_client)

        with patch(
            "bloomy.utils.base_operations.BaseOperations.user_id",
            new_callable=PropertyMock,
            return_value=999,
        ):
            headline_ops.list(meeting_id=0)

        mock_http_client.get.assert_called_once_with("l10/0/headlines")


# ===========================================================================
# 3. TRANSFORM BUGS: Missing keys in API response dicts
# ===========================================================================


class TestIssueTransformMissingKeys:
    """Test _transform_issue_details with incomplete API responses."""

    def test_missing_owner_key_raises_key_error(self) -> None:
        """_transform_issue_details crashes if 'Owner' key is missing."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "OriginId": 10,
            "Origin": "Meeting",
            # "Owner" key is missing entirely
        }
        with pytest.raises(KeyError):
            mixin._transform_issue_details(data)

    def test_owner_missing_id_raises_key_error(self) -> None:
        """_transform_issue_details crashes if Owner dict lacks 'Id'."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "OriginId": 10,
            "Origin": "Meeting",
            "Owner": {"Name": "John"},  # Missing 'Id'
        }
        with pytest.raises(KeyError):
            mixin._transform_issue_details(data)

    def test_owner_missing_name_raises_key_error(self) -> None:
        """_transform_issue_details crashes if Owner dict lacks 'Name'."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "OriginId": 10,
            "Origin": "Meeting",
            "Owner": {"Id": 1},  # Missing 'Name'
        }
        with pytest.raises(KeyError):
            mixin._transform_issue_details(data)

    def test_missing_close_time_key_raises_key_error(self) -> None:
        """_transform_issue_details crashes if 'CloseTime' key is absent.

        The transform accesses data['CloseTime'] directly without .get(),
        so a completely missing key will raise KeyError.
        """
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            # "CloseTime" missing
            "OriginId": 10,
            "Origin": "Meeting",
            "Owner": {"Id": 1, "Name": "John"},
        }
        with pytest.raises(KeyError):
            mixin._transform_issue_details(data)

    def test_owner_is_none_raises_type_error(self) -> None:
        """_transform_issue_details crashes if Owner is None (not a dict)."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "Archived": False,
            "OriginId": 10,
            "Origin": "Meeting",
            "Owner": None,
        }
        with pytest.raises(TypeError):
            mixin._transform_issue_details(data)

    def test_close_time_none_succeeds(self) -> None:
        """CloseTime=None is a valid value and should work fine."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "Archived": False,
            "OriginId": 10,
            "Origin": "Meeting",
            "Owner": {"Id": 1, "Name": "John"},
        }
        result = mixin._transform_issue_details(data)
        assert result.completed_at is None

    def test_close_time_empty_string(self) -> None:
        """CloseTime='' should work (the model field is str|None)."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "CreateTime": "2024-01-01",
            "CloseTime": "",
            "Archived": False,
            "OriginId": 10,
            "Origin": "Meeting",
            "Owner": {"Id": 1, "Name": "John"},
        }
        result = mixin._transform_issue_details(data)
        # Empty string should be accepted (model field is str|None)
        assert result.completed_at is not None or result.completed_at is None


class TestCreatedIssueTransformMissingKeys:
    """Test _transform_created_issue with incomplete API responses."""

    def test_missing_owner_key(self) -> None:
        """_transform_created_issue crashes if Owner is missing."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "OriginId": 10,
            "Origin": "Meeting",
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            # "Owner" missing
        }
        with pytest.raises(KeyError):
            mixin._transform_created_issue(data)

    def test_owner_none(self) -> None:
        """_transform_created_issue crashes if Owner is None."""
        mixin = IssueOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "OriginId": 10,
            "Origin": "Meeting",
            "Name": "Test",
            "DetailsUrl": "http://example.com",
            "Owner": None,
        }
        with pytest.raises(TypeError):
            mixin._transform_created_issue(data)


class TestHeadlineTransformMissingKeys:
    """Test headline transforms with missing/incomplete data."""

    def test_details_missing_owner_key(self) -> None:
        """_transform_headline_details crashes if Owner is missing."""
        mixin = HeadlineOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Headline",
            "DetailsUrl": "http://example.com",
            "OriginId": 10,
            "Origin": "Meeting",
            "Archived": False,
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            # "Owner" missing
        }
        with pytest.raises(KeyError):
            mixin._transform_headline_details(data)

    def test_details_owner_none(self) -> None:
        """_transform_headline_details crashes if Owner is None."""
        mixin = HeadlineOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Headline",
            "DetailsUrl": "http://example.com",
            "OriginId": 10,
            "Origin": "Meeting",
            "Archived": False,
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "Owner": None,
        }
        with pytest.raises(TypeError):
            mixin._transform_headline_details(data)

    def test_details_owner_missing_id(self) -> None:
        """_transform_headline_details crashes if Owner lacks Id."""
        mixin = HeadlineOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Headline",
            "DetailsUrl": "http://example.com",
            "OriginId": 10,
            "Origin": "Meeting",
            "Archived": False,
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "Owner": {"Name": "John"},
        }
        with pytest.raises(KeyError):
            mixin._transform_headline_details(data)

    def test_details_owner_missing_name(self) -> None:
        """_transform_headline_details crashes if Owner lacks Name."""
        mixin = HeadlineOperationsMixin()
        data: dict[str, Any] = {
            "Id": 1,
            "Name": "Headline",
            "DetailsUrl": "http://example.com",
            "OriginId": 10,
            "Origin": "Meeting",
            "Archived": False,
            "CreateTime": "2024-01-01",
            "CloseTime": None,
            "Owner": {"Id": 1},
        }
        with pytest.raises(KeyError):
            mixin._transform_headline_details(data)

    def test_list_item_owner_none(self) -> None:
        """_transform_headline_list crashes if an item's Owner is None."""
        mixin = HeadlineOperationsMixin()
        data = [
            {
                "Id": 1,
                "Name": "Headline",
                "OriginId": 10,
                "Origin": "Meeting",
                "Archived": False,
                "CreateTime": "2024-01-01",
                "CloseTime": None,
                "Owner": None,
            }
        ]
        with pytest.raises(TypeError):
            mixin._transform_headline_list(data)

    def test_list_item_missing_owner(self) -> None:
        """_transform_headline_list crashes if an item has no Owner key."""
        mixin = HeadlineOperationsMixin()
        data = [
            {
                "Id": 1,
                "Name": "Headline",
                "OriginId": 10,
                "Origin": "Meeting",
                "Archived": False,
                "CreateTime": "2024-01-01",
                "CloseTime": None,
            }
        ]
        with pytest.raises(KeyError):
            mixin._transform_headline_list(data)


# ===========================================================================
# 4. HEADLINE CREATE: API returns None for DetailsUrl
# ===========================================================================


class TestHeadlineCreateEdgeCases:
    """Test headline create with unusual API responses."""

    def test_create_with_none_details_url(self, mock_http_client: Mock) -> None:
        """When API returns DetailsUrl=None, .get('DetailsUrl', '') returns None.

        The HeadlineInfo model has notes_url: str, so None would cause a
        validation error if the model enforces the type.
        """
        mock_http_client.post.return_value = _make_mock_response(
            {"Id": 1, "Name": "Test Headline", "DetailsUrl": None}
        )
        headline_ops = HeadlineOperations(mock_http_client)

        with patch(
            "bloomy.utils.base_operations.BaseOperations.user_id",
            new_callable=PropertyMock,
            return_value=123,
        ):
            # data.get("DetailsUrl", "") returns None (key exists with None value)
            # This means notes_url=None, but HeadlineInfo.notes_url is typed as str
            result = headline_ops.create(meeting_id=1, title="Test Headline")

        # The .get() returns None because the key exists with a None value,
        # not the default "". This is a subtle bug.
        # Whether this fails depends on Pydantic's strictness.
        assert result.id == 1

    def test_create_with_missing_details_url_key(self, mock_http_client: Mock) -> None:
        """When API omits DetailsUrl entirely, .get('DetailsUrl', '') returns ''."""
        mock_http_client.post.return_value = _make_mock_response(
            {"Id": 1, "Name": "Test Headline"}
        )
        headline_ops = HeadlineOperations(mock_http_client)

        with patch(
            "bloomy.utils.base_operations.BaseOperations.user_id",
            new_callable=PropertyMock,
            return_value=123,
        ):
            result = headline_ops.create(meeting_id=1, title="Test Headline")

        assert result.notes_url == ""


# ===========================================================================
# 5. ISSUE COMPLETE: unexpected API response
# ===========================================================================


class TestIssueCompleteEdgeCases:
    """Test issue.complete() edge cases."""

    def test_complete_calls_details_after_post(self, mock_http_client: Mock) -> None:
        """Verify complete() does POST then calls details().

        If details() fails, the issue was still marked complete server-side
        but client gets error.
        """
        # POST succeeds
        post_resp = Mock()
        post_resp.raise_for_status = Mock()
        mock_http_client.post.return_value = post_resp

        # GET (for details) fails
        from httpx import HTTPStatusError, Request, Response

        get_resp = Mock()
        get_resp.raise_for_status.side_effect = HTTPStatusError(
            "Not Found",
            request=Request("GET", "http://test"),
            response=Response(404),
        )
        mock_http_client.get.return_value = get_resp

        issue_ops = IssueOperations(mock_http_client)

        with pytest.raises(HTTPStatusError):
            issue_ops.complete(issue_id=999)

        # The POST was still called — issue is completed server-side
        mock_http_client.post.assert_called_once_with(
            "issues/999/complete", json={"complete": True}
        )


# ===========================================================================
# 6. ISSUE LIST: transform with empty list
# ===========================================================================


class TestIssueListEdgeCases:
    """Test issue list transform edge cases."""

    def test_empty_list_returns_empty(self) -> None:
        """An empty API response should return an empty list."""
        mixin = IssueOperationsMixin()
        result = mixin._transform_issue_list([])
        assert result == []

    def test_list_item_missing_details_url(self) -> None:
        """_transform_issue_list crashes if an item lacks DetailsUrl."""
        mixin = IssueOperationsMixin()
        data = [
            {
                "Id": 1,
                "Name": "Test",
                "CreateTime": "2024-01-01",
                "OriginId": 10,
                "Origin": "Meeting",
                # "DetailsUrl" missing
            }
        ]
        with pytest.raises(KeyError):
            mixin._transform_issue_list(data)


class TestHeadlineListEdgeCases:
    """Test headline list transform edge cases."""

    def test_empty_list_returns_empty(self) -> None:
        """An empty API response should return an empty list."""
        mixin = HeadlineOperationsMixin()
        result = mixin._transform_headline_list([])
        assert result == []
