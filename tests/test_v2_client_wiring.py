"""Tests for the v1/v2 namespace wiring on `Client`/`AsyncClient`."""

from __future__ import annotations

from unittest.mock import patch

from bloomy import AsyncClient, Client
from bloomy.v1 import V1, AsyncV1
from bloomy.v2 import V2, AsyncV2


class TestClientV1V2Wiring:
    """Tests for `Client.v1`/`Client.v2` and the top-level aliases."""

    def test_v1_and_v2_namespaces_exist(self) -> None:
        """`client.v1` and `client.v2` are the expected namespace types."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")

            assert isinstance(client.v1, V1)
            assert isinstance(client.v2, V2)

    def test_top_level_attributes_are_v1_aliases(self) -> None:
        """Top-level attributes are the SAME objects as `client.v1.*`."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")

            assert client.user is client.v1.user
            assert client.todo is client.v1.todo
            assert client.meeting is client.v1.meeting
            assert client.goal is client.v1.goal
            assert client.scorecard is client.v1.scorecard
            assert client.issue is client.v1.issue
            assert client.headline is client.v1.headline

    def test_v2_namespace_has_user_meeting_issue(self) -> None:
        """`client.v2` exposes `user`, `meeting`, and `issue` operations."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")

            assert client.v2.user is not None
            assert client.v2.meeting is not None
            assert client.v2.issue is not None

    def test_default_graphql_url_derived_from_base_url(self) -> None:
        """The default `graphql_url` is the base URL's scheme+host plus `/graphql/`."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")

            assert client._graphql_url == "https://app.bloomgrowth.com/graphql/"

    def test_default_graphql_url_follows_custom_base_url(self) -> None:
        """A custom `base_url` produces a matching default `graphql_url`."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(
                api_key="test-key", base_url="https://staging.example.com/api/v1"
            )

            assert client._graphql_url == "https://staging.example.com/graphql/"

    def test_explicit_graphql_url_overrides_default(self) -> None:
        """An explicit `graphql_url` is used as-is."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(
                api_key="test-key", graphql_url="https://custom.example.com/gql"
            )

            assert client._graphql_url == "https://custom.example.com/gql"

    def test_v1_and_v2_share_the_same_http_client(self) -> None:
        """v1 and v2 operations reuse the SAME httpx client instance."""
        with patch("bloomy.client.httpx.Client"):
            client = Client(api_key="test-key")

            assert client.v1.user._client is client._client
            assert client.v2.user._client is client._client


class TestAsyncClientV1V2Wiring:
    """Tests for `AsyncClient.v1`/`AsyncClient.v2` and the top-level aliases."""

    def test_v1_and_v2_namespaces_exist(self) -> None:
        """`client.v1` and `client.v2` are the expected namespace types."""
        with patch("bloomy.async_client.httpx.AsyncClient"):
            client = AsyncClient(api_key="test-key")

            assert isinstance(client.v1, AsyncV1)
            assert isinstance(client.v2, AsyncV2)

    def test_top_level_attributes_are_v1_aliases(self) -> None:
        """Top-level attributes are the SAME objects as `client.v1.*`."""
        with patch("bloomy.async_client.httpx.AsyncClient"):
            client = AsyncClient(api_key="test-key")

            assert client.user is client.v1.user
            assert client.todo is client.v1.todo
            assert client.meeting is client.v1.meeting
            assert client.goal is client.v1.goal
            assert client.scorecard is client.v1.scorecard
            assert client.issue is client.v1.issue
            assert client.headline is client.v1.headline

    def test_default_graphql_url_derived_from_base_url(self) -> None:
        """The default `graphql_url` is the base URL's scheme+host plus `/graphql/`."""
        with patch("bloomy.async_client.httpx.AsyncClient"):
            client = AsyncClient(api_key="test-key")

            assert client._graphql_url == "https://app.bloomgrowth.com/graphql/"

    def test_explicit_graphql_url_overrides_default(self) -> None:
        """An explicit `graphql_url` is used as-is."""
        with patch("bloomy.async_client.httpx.AsyncClient"):
            client = AsyncClient(
                api_key="test-key", graphql_url="https://custom.example.com/gql"
            )

            assert client._graphql_url == "https://custom.example.com/gql"

    def test_v1_and_v2_share_the_same_http_client(self) -> None:
        """v1 and v2 operations reuse the SAME httpx client instance."""
        with patch("bloomy.async_client.httpx.AsyncClient"):
            client = AsyncClient(api_key="test-key")

            assert client.v1.user._client is client._client
            assert client.v2.user._client is client._client
