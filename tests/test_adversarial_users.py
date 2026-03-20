"""Adversarial tests for Users operations, Configuration, and Client.

These tests deliberately feed malformed, missing, and unexpected data to find
bugs, crashes, and unhandled edge cases in the user-related code paths.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import yaml

from bloomy.async_client import AsyncClient
from bloomy.client import Client
from bloomy.configuration import Configuration
from bloomy.exceptions import ConfigurationError
from bloomy.models import (
    DirectReport,
    Position,
    UserDetails,
    UserListItem,
    UserSearchResult,
)
from bloomy.operations.async_.users import AsyncUserOperations
from bloomy.operations.mixins.users_transform import UserOperationsMixin
from bloomy.operations.users import UserOperations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_http_client(json_return: Any = None, side_effect: Any = None) -> Mock:
    """Build a mock httpx.Client whose .get() returns controllable JSON.

    Returns:
        A mock httpx.Client.

    """
    client = Mock(spec=httpx.Client)
    resp = Mock(spec=httpx.Response)
    resp.raise_for_status = Mock()
    if side_effect is not None:
        resp.json.side_effect = side_effect
        client.get.return_value = resp
    elif json_return is not None:
        resp.json.return_value = json_return
        client.get.return_value = resp
    else:
        client.get.return_value = resp
    return client


def _make_async_mock_http_client(json_return: Any = None) -> AsyncMock:
    """Build a mock httpx.AsyncClient whose .get() returns controllable JSON.

    Returns:
        A mock httpx.AsyncClient.

    """
    client = AsyncMock(spec=httpx.AsyncClient)
    resp = Mock(spec=httpx.Response)
    resp.raise_for_status = Mock()
    resp.json.return_value = json_return
    client.get.return_value = resp
    return client


# ===========================================================================
# 1. UserOperationsMixin — transform methods with malformed data
# ===========================================================================


class TestUserTransformMalformedData:
    """Attack the mixin transform methods with bad API responses."""

    def setup_method(self) -> None:
        """Create a fresh mixin for each test."""
        self.mixin = UserOperationsMixin()

    # -- _transform_user_details -----------------------------------------

    def test_user_details_missing_id_key(self) -> None:
        """API returns a dict without 'Id'."""
        with pytest.raises(KeyError, match="Id"):
            self.mixin._transform_user_details({"Name": "x", "ImageUrl": "u"})

    def test_user_details_missing_name_key(self) -> None:
        """API returns a dict without 'Name'."""
        with pytest.raises(KeyError, match="Name"):
            self.mixin._transform_user_details({"Id": 1, "ImageUrl": "u"})

    def test_user_details_missing_image_url_key(self) -> None:
        """API returns a dict without 'ImageUrl'."""
        with pytest.raises(KeyError, match="ImageUrl"):
            self.mixin._transform_user_details({"Id": 1, "Name": "x"})

    def test_user_details_completely_empty_dict(self) -> None:
        """API returns an empty dict."""
        with pytest.raises(KeyError):
            self.mixin._transform_user_details({})

    def test_user_details_none_values(self) -> None:
        """API returns None for all values — model rejects them."""
        # Pydantic should reject None for int field 'id'
        with pytest.raises((TypeError, ValueError)):
            self.mixin._transform_user_details(
                {"Id": None, "Name": None, "ImageUrl": None}
            )

    def test_user_details_wrong_type_id_string(self) -> None:
        """API returns string ID — Pydantic may coerce it."""
        result = self.mixin._transform_user_details(
            {"Id": "999", "Name": "x", "ImageUrl": "u"}
        )
        # Pydantic coerces "999" → 999
        assert result.id == 999

    def test_user_details_wrong_type_id_non_numeric_string(self) -> None:
        """API returns non-numeric string ID."""
        with pytest.raises((TypeError, ValueError)):
            self.mixin._transform_user_details(
                {"Id": "not-a-number", "Name": "x", "ImageUrl": "u"}
            )

    def test_user_details_extra_fields_ignored(self) -> None:
        """Extra fields in the API response should not break parsing."""
        result = self.mixin._transform_user_details(
            {"Id": 1, "Name": "x", "ImageUrl": "u", "Unexpected": True, "Foo": [1, 2]}
        )
        assert result.id == 1

    def test_user_details_with_empty_direct_reports(self) -> None:
        """Passing empty list for direct_reports."""
        result = self.mixin._transform_user_details(
            {"Id": 1, "Name": "x", "ImageUrl": "u"}, direct_reports=[]
        )
        assert result.direct_reports == []

    def test_user_details_with_empty_positions(self) -> None:
        """Passing empty list for positions."""
        result = self.mixin._transform_user_details(
            {"Id": 1, "Name": "x", "ImageUrl": "u"}, positions=[]
        )
        assert result.positions == []

    # -- _transform_direct_reports ---------------------------------------

    def test_direct_reports_missing_keys(self) -> None:
        """Direct report entry missing required keys."""
        with pytest.raises(KeyError):
            self.mixin._transform_direct_reports([{"Id": 1}])

    def test_direct_reports_empty_list(self) -> None:
        """Empty list should return empty list."""
        assert self.mixin._transform_direct_reports([]) == []

    def test_direct_reports_none_input(self) -> None:
        """None instead of list should raise TypeError."""
        with pytest.raises(TypeError):
            self.mixin._transform_direct_reports(None)  # type: ignore[arg-type]

    def test_direct_reports_entry_with_none_id(self) -> None:
        """Report with None ID."""
        with pytest.raises((TypeError, ValueError)):
            self.mixin._transform_direct_reports(
                [{"Id": None, "Name": "x", "ImageUrl": "u"}]
            )

    # -- _transform_positions --------------------------------------------

    def test_positions_missing_group_key(self) -> None:
        """Position entry missing 'Group'."""
        with pytest.raises(KeyError, match="Group"):
            self.mixin._transform_positions([{"Id": 1}])

    def test_positions_missing_position_inside_group(self) -> None:
        """Group dict missing 'Position' key."""
        with pytest.raises(KeyError, match="Position"):
            self.mixin._transform_positions([{"Group": {}}])

    def test_positions_missing_nested_name(self) -> None:
        """Position inside Group missing 'Name'."""
        with pytest.raises(KeyError, match="Name"):
            self.mixin._transform_positions([{"Group": {"Position": {"Id": 1}}}])

    def test_positions_missing_nested_id(self) -> None:
        """Position inside Group missing 'Id'."""
        with pytest.raises(KeyError, match="Id"):
            self.mixin._transform_positions([{"Group": {"Position": {"Name": "x"}}}])

    def test_positions_group_is_none(self) -> None:
        """Group value is None instead of dict."""
        with pytest.raises(TypeError):
            self.mixin._transform_positions([{"Group": None}])

    def test_positions_position_is_none(self) -> None:
        """Position value inside Group is None."""
        with pytest.raises(TypeError):
            self.mixin._transform_positions([{"Group": {"Position": None}}])

    def test_positions_empty_list(self) -> None:
        """Empty list should return empty list."""
        assert self.mixin._transform_positions([]) == []

    def test_positions_none_input(self) -> None:
        """None instead of list should raise TypeError."""
        with pytest.raises(TypeError):
            self.mixin._transform_positions(None)  # type: ignore[arg-type]

    # -- _transform_search_results ---------------------------------------

    def test_search_results_missing_keys(self) -> None:
        """Search result entry missing keys."""
        with pytest.raises(KeyError):
            self.mixin._transform_search_results([{"Id": 1}])

    def test_search_results_none_email(self) -> None:
        """Search result with None email — model field is non-optional str."""
        # Pydantic will try to coerce None to str, which should fail
        with pytest.raises((TypeError, ValueError)):
            self.mixin._transform_search_results(
                [
                    {
                        "Id": 1,
                        "Name": "x",
                        "Description": "d",
                        "Email": None,
                        "OrganizationId": 1,
                        "ImageUrl": "u",
                    }
                ]
            )

    def test_search_results_none_organization_id(self) -> None:
        """Search result with None OrganizationId — model field is int."""
        with pytest.raises((TypeError, ValueError)):
            self.mixin._transform_search_results(
                [
                    {
                        "Id": 1,
                        "Name": "x",
                        "Description": "d",
                        "Email": "e@e.com",
                        "OrganizationId": None,
                        "ImageUrl": "u",
                    }
                ]
            )

    def test_search_results_empty_list(self) -> None:
        """Empty list should return empty list."""
        assert self.mixin._transform_search_results([]) == []

    def test_search_results_empty_strings(self) -> None:
        """All string fields are empty strings — should be accepted."""
        result = self.mixin._transform_search_results(
            [
                {
                    "Id": 1,
                    "Name": "",
                    "Description": "",
                    "Email": "",
                    "OrganizationId": 1,
                    "ImageUrl": "",
                }
            ]
        )
        assert len(result) == 1
        # str_strip_whitespace is on; empty string stays empty
        assert result[0].name == ""

    # -- _transform_user_list --------------------------------------------

    def test_user_list_missing_result_type(self) -> None:
        """User entry missing 'ResultType' key."""
        with pytest.raises(KeyError, match="ResultType"):
            self.mixin._transform_user_list(
                [
                    {
                        "Id": 1,
                        "Name": "x",
                        "Email": "e",
                        "Description": "d",
                        "ImageUrl": "u",
                    }
                ],
                include_placeholders=False,
            )

    def test_user_list_missing_image_url_in_model(self) -> None:
        """User with ResultType=User but missing ImageUrl crashes."""
        with pytest.raises(KeyError, match="ImageUrl"):
            self.mixin._transform_user_list(
                [
                    {
                        "Id": 1,
                        "Name": "x",
                        "Email": "e",
                        "Description": "d",
                        "ResultType": "User",
                    }
                ],
                include_placeholders=False,
            )

    def test_user_list_missing_email_after_filter(self) -> None:
        """User passes filter but is missing 'Email' key for model construction."""
        with pytest.raises(KeyError, match="Email"):
            self.mixin._transform_user_list(
                [
                    {
                        "Id": 1,
                        "Name": "x",
                        "Description": "d",
                        "ImageUrl": "u",
                        "ResultType": "User",
                    }
                ],
                include_placeholders=True,
            )

    def test_user_list_none_image_url(self) -> None:
        """ImageUrl is None — accepted since image_url is now optional.

        Previously this was a bug where None ImageUrl crashed model
        construction. Fix: UserListItem.image_url is now str | None,
        and filtering is email-based.
        """
        result = self.mixin._transform_user_list(
            [
                {
                    "Id": 1,
                    "Name": "x",
                    "Email": "e",
                    "Description": "d",
                    "ImageUrl": None,
                    "ResultType": "User",
                }
            ],
            include_placeholders=False,
        )
        assert len(result) == 1
        assert result[0].image_url is None

    def test_user_list_empty_list(self) -> None:
        """Empty list should return empty list."""
        assert self.mixin._transform_user_list([], include_placeholders=False) == []

    def test_user_list_only_non_user_types(self) -> None:
        """All entries are non-User ResultType."""
        result = self.mixin._transform_user_list(
            [
                {"Id": 1, "Name": "g", "ResultType": "Group", "ImageUrl": "u"},
                {"Id": 2, "Name": "t", "ResultType": "Team", "ImageUrl": "u"},
            ],
            include_placeholders=True,
        )
        assert result == []

    def test_user_list_placeholder_filtering(self) -> None:
        """Verify placeholders are filtered correctly based on flag."""
        users = [
            {
                "Id": 1,
                "Name": "Real",
                "Email": "r@e.com",
                "Description": "d",
                "ImageUrl": "https://img.com/a.jpg",
                "ResultType": "User",
            },
            {
                "Id": 2,
                "Name": "Placeholder",
                "Email": "",
                "Description": "",
                "ImageUrl": "/i/userplaceholder",
                "ResultType": "User",
            },
        ]
        without = self.mixin._transform_user_list(users, include_placeholders=False)
        assert len(without) == 1
        assert without[0].id == 1

        with_ph = self.mixin._transform_user_list(users, include_placeholders=True)
        assert len(with_ph) == 2


# ===========================================================================
# 2. UserOperations (sync) — end-to-end with mock HTTP
# ===========================================================================


class TestUserOperationsAdversarial:
    """Test sync UserOperations with adversarial API responses."""

    def test_details_api_returns_empty_dict(self, mock_user_id: Mock) -> None:
        """API returns {} for user details."""
        client = _make_mock_http_client(json_return={})
        ops = UserOperations(client)
        with pytest.raises(KeyError):
            ops.details()

    def test_details_api_returns_list_instead_of_dict(self, mock_user_id: Mock) -> None:
        """API returns a list instead of a dict."""
        client = _make_mock_http_client(json_return=[{"Id": 1}])
        ops = UserOperations(client)
        with pytest.raises((KeyError, TypeError)):
            ops.details()

    def test_details_api_returns_none_json(self, mock_user_id: Mock) -> None:
        """API returns null JSON body."""
        client = _make_mock_http_client(json_return=None)
        ops = UserOperations(client)
        with pytest.raises(TypeError):
            ops.details()

    def test_details_with_user_id_zero(self) -> None:
        """user_id=0 is technically a valid int but suspicious."""
        client = _make_mock_http_client(
            json_return={"Id": 0, "Name": "Zero", "ImageUrl": "u"}
        )
        ops = UserOperations(client)
        result = ops.details(user_id=0)
        assert result.id == 0
        client.get.assert_called_once_with("users/0")

    def test_details_with_negative_user_id(self) -> None:
        """Negative user_id — SDK should pass it through to API."""
        client = _make_mock_http_client(
            json_return={"Id": -1, "Name": "Neg", "ImageUrl": "u"}
        )
        ops = UserOperations(client)
        result = ops.details(user_id=-1)
        assert result.id == -1
        client.get.assert_called_once_with("users/-1")

    def test_search_empty_string(self) -> None:
        """Search with empty string."""
        client = _make_mock_http_client(json_return=[])
        ops = UserOperations(client)
        result = ops.search("")
        assert result == []
        client.get.assert_called_once_with("search/user", params={"term": ""})

    def test_direct_reports_api_returns_non_list(self) -> None:
        """API returns a dict instead of list for direct reports."""
        client = _make_mock_http_client(json_return={"error": "something"})
        ops = UserOperations(client)
        with pytest.raises(TypeError):
            ops.direct_reports(user_id=1)

    def test_positions_api_returns_string(self) -> None:
        """API returns a raw string instead of JSON list."""
        client = _make_mock_http_client(json_return="not a list")
        ops = UserOperations(client)
        with pytest.raises(TypeError):
            ops.positions(user_id=1)

    def test_list_api_returns_non_list(self) -> None:
        """API returns a dict instead of list for user list."""
        client = _make_mock_http_client(json_return={"users": []})
        ops = UserOperations(client)
        with pytest.raises(TypeError):
            ops.list()

    def test_user_id_property_lazy_loads(self) -> None:
        """user_id property fetches from API when not set."""
        client = _make_mock_http_client(json_return={"Id": 42})
        ops = UserOperations(client)
        uid = ops.user_id
        assert uid == 42
        client.get.assert_called_once_with("users/mine")

    def test_user_id_api_returns_no_id_key(self) -> None:
        """users/mine returns dict without 'Id'."""
        client = _make_mock_http_client(json_return={"Name": "x"})
        ops = UserOperations(client)
        with pytest.raises(KeyError, match="Id"):
            _ = ops.user_id


# ===========================================================================
# 3. AsyncUserOperations — adversarial async tests
# ===========================================================================


class TestAsyncUserOperationsAdversarial:
    """Test async user operations with adversarial inputs."""

    @pytest.mark.asyncio
    async def test_details_api_returns_empty_dict(self) -> None:
        """Async details with empty dict response."""
        client = _make_async_mock_http_client(json_return={})
        ops = AsyncUserOperations(client)
        ops._user_id = 1
        with pytest.raises(KeyError):
            await ops.details(user_id=1)

    @pytest.mark.asyncio
    async def test_get_user_id_lazy_loads(self) -> None:
        """get_user_id fetches from API when not cached."""
        client = _make_async_mock_http_client(json_return={"Id": 77})
        ops = AsyncUserOperations(client)
        uid = await ops.get_user_id()
        assert uid == 77

    @pytest.mark.asyncio
    async def test_user_id_property_raises_without_fetch(self) -> None:
        """user_id property raises RuntimeError if not fetched yet."""
        client = _make_async_mock_http_client(json_return={})
        ops = AsyncUserOperations(client)
        with pytest.raises(RuntimeError, match="User ID not set"):
            _ = ops.user_id

    @pytest.mark.asyncio
    async def test_direct_reports_none_response(self) -> None:
        """API returns None for direct reports."""
        client = _make_async_mock_http_client(json_return=None)
        ops = AsyncUserOperations(client)
        with pytest.raises(TypeError):
            await ops.direct_reports(user_id=1)

    @pytest.mark.asyncio
    async def test_search_results_malformed(self) -> None:
        """API returns list with entries missing keys."""
        client = _make_async_mock_http_client(json_return=[{"Id": 1}])
        ops = AsyncUserOperations(client)
        with pytest.raises(KeyError):
            await ops.search("test")

    @pytest.mark.asyncio
    async def test_positions_deeply_nested_missing(self) -> None:
        """API returns positions with missing nested structure."""
        client = _make_async_mock_http_client(json_return=[{"Group": {}}])
        ops = AsyncUserOperations(client)
        with pytest.raises(KeyError):
            await ops.positions(user_id=1)


# ===========================================================================
# 4. Configuration — adversarial inputs
# ===========================================================================


class TestConfigurationAdversarial:
    """Attack Configuration with missing/corrupt data."""

    def test_no_api_key_anywhere(self) -> None:
        """No key provided, no env var, no config file."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
        ):
            config = Configuration()
            assert config.api_key is None

    def test_empty_string_api_key_direct(self) -> None:
        """Empty string passed as api_key — truthy check may pass or fail."""
        # Empty string is falsy, so it falls through to env var
        # This verifies the `api_key or ...` chain behavior
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
        ):
            config2 = Configuration(api_key="")
            # "" or None => None
            assert config2.api_key is None

    def test_whitespace_only_api_key_stripped(self) -> None:
        """Whitespace-only API key is stripped before the or-chain.

        Fix verified: Configuration strips the key first, producing "".
        The empty string is falsy and falls through the or-chain.
        With no env var or config file, api_key ends up None.
        """
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
        ):
            config = Configuration(api_key="   ")
            # "   ".strip() -> "" which is falsy, falls through or-chain
            assert config.api_key is None

    def test_env_var_takes_precedence_over_file(self) -> None:
        """BG_API_KEY env var should override config file."""
        with (
            patch.dict(os.environ, {"BG_API_KEY": "env-key"}),
            patch.object(Configuration, "_load_api_key", return_value="file-key"),
        ):
            config = Configuration()
            assert config.api_key == "env-key"

    def test_explicit_key_takes_precedence_over_all(self) -> None:
        """Explicit api_key param should override everything."""
        with patch.dict(os.environ, {"BG_API_KEY": "env-key"}):
            config = Configuration(api_key="explicit-key")
            assert config.api_key == "explicit-key"

    def test_load_api_key_corrupt_yaml(self, tmp_path: Path) -> None:
        """Config file contains invalid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(": : : [invalid yaml {{{")

        config = Configuration.__new__(Configuration)
        with patch.object(
            type(config),
            "_config_file",
            new_callable=lambda: property(lambda _: config_file),
        ):
            result = config._load_api_key()
            # Should return None gracefully due to the except clause
            assert result is None

    def test_load_api_key_yaml_without_api_key_field(self, tmp_path: Path) -> None:
        """Config file is valid YAML but missing 'api_key' field."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"version": 1, "other_field": "value"}))

        config = Configuration.__new__(Configuration)
        with patch.object(
            type(config),
            "_config_file",
            new_callable=lambda: property(lambda _: config_file),
        ):
            result = config._load_api_key()
            assert result is None

    def test_load_api_key_yaml_with_none_value(self, tmp_path: Path) -> None:
        """Config file has api_key: null."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"version": 1, "api_key": None}))

        config = Configuration.__new__(Configuration)
        with patch.object(
            type(config),
            "_config_file",
            new_callable=lambda: property(lambda _: config_file),
        ):
            result = config._load_api_key()
            assert result is None

    def test_load_api_key_empty_file(self, tmp_path: Path) -> None:
        """Config file exists but is empty."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        config = Configuration.__new__(Configuration)
        with patch.object(
            type(config),
            "_config_file",
            new_callable=lambda: property(lambda _: config_file),
        ):
            result = config._load_api_key()
            # yaml.safe_load("") returns None; .get() raises AttributeError
            # This is caught by the except clause and returns None
            assert result is None

    def test_load_api_key_binary_content(self, tmp_path: Path) -> None:
        """Config file contains binary garbage."""
        config_file = tmp_path / "config.yaml"
        config_file.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

        config = Configuration.__new__(Configuration)
        with patch.object(
            type(config),
            "_config_file",
            new_callable=lambda: property(lambda _: config_file),
        ):
            result = config._load_api_key()
            # Should be caught by broad except
            assert result is None

    def test_store_api_key_when_none(self) -> None:
        """Storing None api_key raises ConfigurationError."""
        config = Configuration.__new__(Configuration)
        config.api_key = None
        with pytest.raises(ConfigurationError, match="API key is None"):
            config._store_api_key()

    def test_configure_api_key_overwrites_existing(self) -> None:
        """configure_api_key overwrites even if api_key already set."""
        config = Configuration(api_key="old-key")
        with patch.object(config, "_fetch_api_key", return_value="new-key"):
            config.configure_api_key("user", "pass")
            assert config.api_key == "new-key"


# ===========================================================================
# 5. Client — adversarial initialization
# ===========================================================================


class TestClientAdversarial:
    """Attack Client with bad configuration."""

    def test_client_no_api_key_raises(self) -> None:
        """Client without any API key raises ConfigurationError."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            Client()

    def test_client_empty_string_api_key_raises(self) -> None:
        """Client with empty string API key should raise."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            Client(api_key="")

    def test_client_whitespace_api_key_now_raises(self) -> None:
        """Client with whitespace-only API key now raises.

        Fix verified: Configuration strips whitespace, so "   " becomes
        "" which is falsy, triggering the ConfigurationError.
        """
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            Client(api_key="   ")

    def test_client_context_manager(self) -> None:
        """Context manager closes client properly."""
        with patch("bloomy.client.httpx.Client") as mock_cls:
            mock_http = Mock()
            mock_cls.return_value = mock_http
            with Client(api_key="test-key") as c:
                assert c is not None
            mock_http.close.assert_called_once()

    def test_client_double_close(self) -> None:
        """Calling close() twice should not raise."""
        with patch("bloomy.client.httpx.Client") as mock_cls:
            mock_http = Mock()
            mock_cls.return_value = mock_http
            c = Client(api_key="test-key")
            c.close()
            c.close()  # Should not raise

    def test_client_operations_initialized(self) -> None:
        """All operation classes should be initialized."""
        with patch("bloomy.client.httpx.Client"):
            c = Client(api_key="test-key")
            assert c.user is not None
            assert c.todo is not None
            assert c.meeting is not None
            assert c.goal is not None
            assert c.scorecard is not None
            assert c.issue is not None
            assert c.headline is not None


# ===========================================================================
# 6. AsyncClient — adversarial initialization
# ===========================================================================


class TestAsyncClientAdversarial:
    """Attack AsyncClient with bad configuration."""

    def test_async_client_no_api_key_raises(self) -> None:
        """AsyncClient without any API key raises ConfigurationError."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            AsyncClient()

    def test_async_client_empty_string_raises(self) -> None:
        """AsyncClient with empty string API key should raise."""
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            AsyncClient(api_key="")

    def test_async_client_whitespace_key_now_raises(self) -> None:
        """AsyncClient with whitespace key now raises ConfigurationError.

        Fix verified: Configuration strips whitespace, so "   " becomes
        "" which is falsy, triggering the ConfigurationError.
        """
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(Configuration, "_load_api_key", return_value=None),
            pytest.raises(ConfigurationError),
        ):
            AsyncClient(api_key="   ")


# ===========================================================================
# 7. Pydantic model edge cases — user-related models
# ===========================================================================


class TestUserModelsEdgeCases:
    """Test Pydantic models with edge case inputs."""

    def test_user_details_negative_id(self) -> None:
        """Negative ID accepted by the model."""
        u = UserDetails(id=-1, name="x", image_url="u")
        assert u.id == -1

    def test_user_details_very_large_id(self) -> None:
        """Very large ID."""
        u = UserDetails(id=2**63, name="x", image_url="u")
        assert u.id == 2**63

    def test_user_details_whitespace_name_stripped(self) -> None:
        """Whitespace should be stripped due to str_strip_whitespace."""
        u = UserDetails(id=1, name="  John  ", image_url="u")
        assert u.name == "John"

    def test_direct_report_empty_name(self) -> None:
        """Empty name accepted."""
        d = DirectReport(id=1, name="", image_url="u")
        assert d.name == ""

    def test_position_none_name(self) -> None:
        """Position name is optional."""
        p = Position(id=1, name=None)
        assert p.name is None

    def test_user_search_result_all_empty_strings(self) -> None:
        """All string fields empty."""
        u = UserSearchResult(
            id=1, name="", description="", email="", organization_id=1, image_url=""
        )
        assert u.email == ""

    def test_user_list_item_none_position_accepted(self) -> None:
        """UserListItem.position is now optional (str | None) — None is accepted.

        Fix verified: position and image_url are now optional to handle API
        responses where Description or ImageUrl may be null.
        """
        item = UserListItem(id=1, name="x", email="e", position=None, image_url="u")
        assert item.position is None

    def test_user_list_item_none_email_rejected(self) -> None:
        """UserListItem.email is non-optional str — None should be rejected."""
        with pytest.raises((TypeError, ValueError)):
            UserListItem(id=1, name="x", email=None, position="p", image_url="u")  # type: ignore[arg-type]

    def test_user_search_result_float_id_coerced(self) -> None:
        """Float ID should be coerced to int by Pydantic."""
        u = UserSearchResult(
            id=1.0,
            name="x",
            description="d",
            email="e",  # type: ignore[arg-type]
            organization_id=1,
            image_url="u",
        )
        assert u.id == 1
        assert isinstance(u.id, int)

    def test_user_details_assignment_validation(self) -> None:
        """validate_assignment is on — invalid assignment should raise."""
        u = UserDetails(id=1, name="x", image_url="u")
        with pytest.raises((TypeError, ValueError)):
            u.id = "not-a-number"  # type: ignore[assignment]
