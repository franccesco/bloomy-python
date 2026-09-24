"""Transport and shared helpers for the Bloomy v2 (GraphQL) API.

Every v2 entity module builds on the classes in this file: `GraphQLOperations`
for sync operations, `AsyncGraphQLOperations` for async. Both execute
`{query, variables}` documents against the GraphQL endpoint over the SAME
httpx client instance the v1 REST operations use (an absolute URL passed to
`client.post()` overrides the client's `base_url`), and share the error
handling, timestamp conversion, and description ("notes") helpers defined on
`AbstractGraphQLOperations`.

Error handling contract (see `bloomy.exceptions.GraphQLError`):
    - A response body carrying a top-level `errors` array raises
      `GraphQLError`, regardless of HTTP status (validation errors return
      HTTP 400 with `errors`; execution errors return HTTP 200 with
      `errors` alongside `data`).
    - A response that fails to parse as JSON (e.g. a plain-text 401/500)
      falls back to `response.raise_for_status()`.
    - A response that parses as JSON without an `errors` key still goes
      through `response.raise_for_status()` before its `data` is returned,
      so a JSON error body with no `errors` array (or an expired-token 401
      with an empty body) still raises a clear `httpx.HTTPStatusError`
      instead of failing deep inside `data` access.
    - Mutations shaped `{success message errorDetails{message}}` (the
      `GraphQLResponseOfBoolean`/`OfString`/`Base` family) raise
      `GraphQLError` when `success` is `false`, via `_check_mutation_result`.
    - A by-id query returning `null` for the requested entity (unknown or
      not visible to the caller), and a `Create*` mutation returning a
      `null` result or an `id` of `0`, both raise `GraphQLError` via
      `_require_entity`/`_require_created_id` rather than failing deep
      inside a model/transform call.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, cast

from ..exceptions import GraphQLError

if TYPE_CHECKING:
    import httpx

_TAG_RE = re.compile(r"<[^>]+>")

#: Fields shared by every `{success message errorDetails{message}}` mutation
#: result (the `GraphQLResponseOfBoolean` / `OfString` / `Base` family).
MUTATION_RESULT_FIELDS = "success message errorDetails { message }"

_CREATE_NOTE_MUTATION = f"""
mutation($text: String) {{
  CreateNote(text: $text) {{
    data
    {MUTATION_RESULT_FIELDS}
  }}
}}
"""

_GET_AUTHENTICATED_USER_ID_MUTATION = "mutation { getAuthenticatedUserId { id } }"


def prepare_note_text(text: str) -> str:
    """Escape plain text for Etherpad's `setHTML`, as `CreateNote` expects.

    Args:
        text: The plain text to store.

    Returns:
        HTML-escaped text with newlines turned into `<br>`.

    """
    return html.escape(text).replace("\n", "<br>")


def extract_notes(data: dict[str, Any]) -> str | None:
    """Extract plain description text from a notes projection.

    Expects `notesText`, `localHtml`, and `collaborationEnabled` to have been
    selected on `data` (selecting `notesText` without `collaborationEnabled`
    makes the API resolve it to `""`).

    This is a module-level function, not only a method on
    `AbstractGraphQLOperations`, so that entity mixins (which are combined
    with both the sync and async base classes, and so cannot themselves
    inherit from `AbstractGraphQLOperations`) can import and call it
    directly instead of going through `self`.

    Args:
        data: The raw GraphQL object carrying the notes fields.

    Returns:
        The plain description text, or `None` if empty.

    """
    if data.get("collaborationEnabled"):
        text = (data.get("notesText") or "").rstrip("\n")
    else:
        local_html = data.get("localHtml") or ""
        text = html.unescape(_TAG_RE.sub("", local_html)).strip()
    return text or None


def merge_nodes(
    *node_lists: list[dict[str, Any]], date_field: str = "dateCreated"
) -> list[dict[str, Any]]:
    """Merge raw GraphQL node lists, deduping by id and sorting by creation date.

    Used to combine the results of a single query that selects several
    connections conditionally with `@include(if: ...)` (e.g. `issues` plus
    `recentlySolvedIssues`/`archivedIssues`) into one ordered list, since each
    connection is independently ordered but the combined result is not.

    Args:
        *node_lists: Raw node lists to merge, in any order.
        date_field: The raw field name holding each node's creation
            timestamp, used as the primary sort key.

    Returns:
        The merged nodes with each id appearing once (first occurrence
        wins), sorted by `(date_field, id)`.

    """
    seen: dict[int, dict[str, Any]] = {}
    for nodes in node_lists:
        for node in nodes:
            seen.setdefault(node["id"], node)
    return sorted(seen.values(), key=lambda node: (node[date_field], node["id"]))


def dig_nodes(data: dict[str, Any] | None, *keys: str) -> list[dict[str, Any]]:
    """Walk nested dict keys (each defaulting to `{}`) and read a `nodes` list.

    GraphQL connection results are shaped like
    `{"meeting": {"issues": {"nodes": [...]}}}`; any level can be missing
    (e.g. a `null` `meeting`), so this walks each key defensively instead of
    chaining `.get(...) or {}` inline (which loses precise typing under
    strict mode once an untyped `{}` fallback enters the chain).

    Args:
        data: The raw GraphQL `data` object (or a nested object within it).
        *keys: The nested keys to walk before reading `nodes`.

    Returns:
        The `nodes` list found this way, or an empty list if any step, or
        `nodes` itself, is missing.

    """
    current: dict[str, Any] = data or {}
    for key in keys:
        current = current.get(key) or {}
    nodes = current.get("nodes")
    return list(nodes) if nodes else []


class AbstractGraphQLOperations:
    """Shared, transport-agnostic logic for v2 (GraphQL) operations."""

    def __init__(self, client: Any, graphql_url: str) -> None:
        """Initialize the operations class.

        Args:
            client: The httpx client (sync or async) to use for requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        self._client = client
        self._graphql_url = graphql_url
        self._user_id: int | None = None

    # -- request/response plumbing ------------------------------------------------

    def _build_payload(
        self, query: str, variables: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build the JSON body for a GraphQL request.

        Returns:
            A `{"query": ..., "variables": ...}` dictionary.

        """
        return {"query": query, "variables": variables or {}}

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        """Parse a GraphQL HTTP response into its `data` object.

        Args:
            response: The raw httpx response from the GraphQL endpoint.

        Returns:
            The `data` object of the response (empty dict if absent).

        Raises:
            GraphQLError: If the response body carries a JSON `errors` array.
            ValueError: If the response body is not valid JSON despite a
                successful (2xx) status, re-raising the original JSON-decode
                error (a non-2xx status raises `httpx.HTTPStatusError`
                instead, via `response.raise_for_status()`).

        """
        try:
            raw: Any = response.json()
        except ValueError:
            response.raise_for_status()
            raise

        payload = cast("dict[str, Any]", raw) if isinstance(raw, dict) else {}
        errors: list[dict[str, Any]] = payload.get("errors") or []
        if errors:
            message = "; ".join(
                error.get("message", "Unknown GraphQL error") for error in errors
            )
            raise GraphQLError(
                message or "GraphQL request failed",
                status_code=response.status_code,
                errors=errors,
            )

        response.raise_for_status()
        return payload.get("data") or {}

    def _check_mutation_result(
        self, result: dict[str, Any] | None, *, action: str
    ) -> None:
        """Raise `GraphQLError` for a failed `{success message errorDetails}` result.

        Args:
            result: The mutation's result object (e.g. `data["EditIssue"]`).
            action: A short description of the mutation, used in the error
                message when the result is missing entirely.

        Raises:
            GraphQLError: If `result` is missing or `success` is falsy.

        """
        if result is None:
            raise GraphQLError(f"{action} failed: no result returned")
        if not result.get("success", False):
            error_details: list[dict[str, Any]] = result.get("errorDetails") or []
            detail_messages = [
                detail.get("message", "") for detail in error_details if detail
            ]
            message = (
                result.get("message")
                or "; ".join(filter(None, detail_messages))
                or f"{action} failed"
            )
            raise GraphQLError(message, errors=error_details)

    # -- entity presence -------------------------------------------------------

    @staticmethod
    def _require_entity(
        data: dict[str, Any], field: str, entity_id: int, label: str
    ) -> dict[str, Any]:
        """Get a required nested entity object from a GraphQL response, or raise.

        A by-id query (e.g. `issue(id: $id)`) returns `null` for that field
        instead of a top-level GraphQL error when the id is unknown or not
        visible to the caller, so every `details()`-style read needs this
        check before handing the raw object to a model/transform.

        Args:
            data: The raw GraphQL `data` object.
            field: The key in `data` holding the entity object (e.g.
                `"issue"`).
            entity_id: The id that was requested, used in the error message.
            label: A human-readable label for the entity (e.g. `"Issue"`).

        Returns:
            The entity object.

        Raises:
            GraphQLError: If `data[field]` is missing or `null`.

        """
        entity = data.get(field)
        if not entity:
            raise GraphQLError(f"{label} {entity_id} not found")
        return entity

    @staticmethod
    def _require_created_id(result: dict[str, Any] | None, *, label: str) -> int:
        """Get a newly created entity's id from a `Create*` mutation result, or raise.

        Some v2 `Create*` mutations (e.g. `CreateGoal`) return `IdModel { id }`
        and report a failure by returning a `null` result, or an `id` of `0`,
        rather than a top-level GraphQL error -- re-reading id `0` would
        otherwise surface as a confusing "not found" from the follow-up read.

        Args:
            result: The mutation's result object (e.g. `data["CreateGoal"]`).
            label: A human-readable label for the entity being created, used
                in the error message (e.g. `"goal"`).

        Returns:
            The newly created entity's id.

        Raises:
            GraphQLError: If `result` is missing, or its `id` is missing or
                `0`.

        """
        entity_id = (result or {}).get("id")
        if not entity_id:
            raise GraphQLError(f"create {label} failed: no id returned")
        return int(entity_id)

    # -- timestamps -----------------------------------------------------------

    @staticmethod
    def _to_timestamp(value: datetime | date | float | int) -> float:
        """Convert a datetime/date/number into unix seconds (UTC).

        A naive `datetime` is treated as UTC. A `date` becomes 00:00 UTC of
        that day.

        Args:
            value: The value to convert.

        Returns:
            Unix seconds as a float.

        """
        if isinstance(value, datetime):
            aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
            return aware.timestamp()
        if isinstance(value, date):
            return datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp()
        return float(value)

    @staticmethod
    def _now_timestamp() -> float:
        """Return the current time as unix seconds (UTC).

        Returns:
            Unix seconds as a float.

        """
        return datetime.now(tz=UTC).timestamp()

    # -- descriptions ("notes") -------------------------------------------------
    # See the module-level `prepare_note_text`/`extract_notes` docstrings.

    _prepare_note_text = staticmethod(prepare_note_text)
    _extract_notes = staticmethod(extract_notes)


class GraphQLOperations(AbstractGraphQLOperations):
    """Sync base class for v2 (GraphQL) operation classes."""

    def __init__(self, client: httpx.Client, graphql_url: str) -> None:
        """Initialize the operations class.

        Args:
            client: The sync HTTP client to use for GraphQL requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        super().__init__(client, graphql_url)
        self._client: httpx.Client = client

    @property
    def user_id(self) -> int:
        """Get the current user's ID, fetching it if needed.

        Returns:
            The user ID of the authenticated user.

        """
        if self._user_id is None:
            self._user_id = self._fetch_authenticated_user_id()
        return self._user_id

    def _fetch_authenticated_user_id(self) -> int:
        """Fetch the authenticated user's ID via `getAuthenticatedUserId`.

        Returns:
            The user ID of the authenticated user.

        """
        data = self._execute(_GET_AUTHENTICATED_USER_ID_MUTATION)
        return int(data["getAuthenticatedUserId"]["id"])

    def _execute(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL document and return its `data` object.

        Args:
            query: The GraphQL query or mutation document.
            variables: The GraphQL variables for the document, if any.

        Returns:
            The `data` object of the response. See `_parse_response` for the
            errors this can raise.

        """
        response = self._client.post(
            self._graphql_url, json=self._build_payload(query, variables)
        )
        return self._parse_response(response)

    def _run_mutation(
        self,
        query: str,
        variables: dict[str, Any] | None,
        *,
        root_field: str,
        action: str,
    ) -> dict[str, Any]:
        """Execute a mutation and check its `{success message errorDetails}` result.

        Args:
            query: The GraphQL mutation document.
            variables: The GraphQL variables for the document.
            root_field: The mutation's root field name in `data` (e.g. `EditIssue`).
            action: A short description of the mutation, used in error messages.

        Returns:
            The mutation's result object (`data[root_field]`). See
            `_check_mutation_result` for the errors this can raise.

        """
        data = self._execute(query, variables)
        result = data.get(root_field)
        self._check_mutation_result(result, action=action)
        return result or {}

    def _create_note(self, text: str) -> str:
        """Create a new Etherpad note pad from plain text.

        Args:
            text: The plain text to store. Newlines and HTML-sensitive
                characters are escaped for Etherpad automatically.

        Returns:
            The new pad's id, for use as `notesId` on a create/edit input.
            See `_check_mutation_result` for the errors this can raise.

        """
        result = self._run_mutation(
            _CREATE_NOTE_MUTATION,
            {"text": self._prepare_note_text(text)},
            root_field="CreateNote",
            action="CreateNote",
        )
        return str(result["data"])


class AsyncGraphQLOperations(AbstractGraphQLOperations):
    """Async base class for v2 (GraphQL) operation classes."""

    def __init__(self, client: httpx.AsyncClient, graphql_url: str) -> None:
        """Initialize the async operations class.

        Args:
            client: The async HTTP client to use for GraphQL requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        super().__init__(client, graphql_url)
        self._client: httpx.AsyncClient = client

    @property
    def user_id(self) -> int:
        """Get the cached user ID.

        For async operations, use `get_user_id()` to fetch from the API.

        Raises:
            RuntimeError: If the user ID has not been fetched yet.

        """
        if self._user_id is None:
            raise RuntimeError("User ID not set. Use get_user_id() to fetch from API.")
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        """Set the cached user ID."""
        self._user_id = value

    async def get_user_id(self) -> int:
        """Get the current user's ID, fetching it if needed.

        Returns:
            The user ID of the authenticated user.

        """
        if self._user_id is None:
            self._user_id = await self._fetch_authenticated_user_id()
        return self._user_id

    async def _fetch_authenticated_user_id(self) -> int:
        """Fetch the authenticated user's ID via `getAuthenticatedUserId`.

        Returns:
            The user ID of the authenticated user.

        """
        data = await self._execute(_GET_AUTHENTICATED_USER_ID_MUTATION)
        return int(data["getAuthenticatedUserId"]["id"])

    async def _execute(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL document and return its `data` object.

        Args:
            query: The GraphQL query or mutation document.
            variables: The GraphQL variables for the document, if any.

        Returns:
            The `data` object of the response. See `_parse_response` for the
            errors this can raise.

        """
        response = await self._client.post(
            self._graphql_url, json=self._build_payload(query, variables)
        )
        return self._parse_response(response)

    async def _run_mutation(
        self,
        query: str,
        variables: dict[str, Any] | None,
        *,
        root_field: str,
        action: str,
    ) -> dict[str, Any]:
        """Execute a mutation and check its `{success message errorDetails}` result.

        Args:
            query: The GraphQL mutation document.
            variables: The GraphQL variables for the document.
            root_field: The mutation's root field name in `data` (e.g. `EditIssue`).
            action: A short description of the mutation, used in error messages.

        Returns:
            The mutation's result object (`data[root_field]`). See
            `_check_mutation_result` for the errors this can raise.

        """
        data = await self._execute(query, variables)
        result = data.get(root_field)
        self._check_mutation_result(result, action=action)
        return result or {}

    async def _create_note(self, text: str) -> str:
        """Create a new Etherpad note pad from plain text.

        Args:
            text: The plain text to store. Newlines and HTML-sensitive
                characters are escaped for Etherpad automatically.

        Returns:
            The new pad's id, for use as `notesId` on a create/edit input.
            See `_check_mutation_result` for the errors this can raise.

        """
        result = await self._run_mutation(
            _CREATE_NOTE_MUTATION,
            {"text": self._prepare_note_text(text)},
            root_field="CreateNote",
            action="CreateNote",
        )
        return str(result["data"])
