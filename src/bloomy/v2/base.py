"""Transport and shared helpers for the Bloomy v2 (GraphQL) API.

`GraphQLOperations` (sync) and `AsyncGraphQLOperations` (async) post
`{query, variables}` documents over the same httpx client the v1 REST
operations use: an absolute URL passed to `client.post()` overrides the
client's `base_url`. The module-level helpers carry no state, so entity mixins
(shared by the sync and async classes) and the models can call them directly.
"""

from __future__ import annotations

import asyncio
import html
import re
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from ..exceptions import GraphQLError
from ..utils.abstract_operations import AbstractOperations

if TYPE_CHECKING:
    import httpx

_TAG_RE = re.compile(r"<[^>]+>")

#: Fields of every `{success message errorDetails{message}}` mutation result.
MUTATION_RESULT_FIELDS = "success message errorDetails { message }"
#: Description ("notes") fields read by `extract_notes`.
NOTES_FIELDS = "notesId notesText localHtml collaborationEnabled"
#: An entity's owner, validated into `UserRef`.
USER_REF_FIELDS = "assignee { id fullName }"
#: An entity's meeting, validated into `MeetingRef`.
MEETING_REF_FIELDS = "meeting { id name }"
#: Fields of a goal milestone, validated into `Milestone`.
MILESTONE_FIELDS = "id goalId title dueDate completed status dateCreated"
#: A goal's `milestones` connection, read by both goal and milestone queries.
#: The API already drops soft-deleted milestones; the filter matches the web app.
MILESTONES_CONNECTION = f"""
milestones(
  where: {{ and: [{{ dateDeleted: {{ eq: null }} }}] }}
  order: [{{ dueDate: ASC }}]
) {{
  nodes {{
    {MILESTONE_FIELDS}
  }}
}}
"""

_CREATE_NOTE_MUTATION = f"""
mutation($text: String) {{
  CreateNote(text: $text) {{
    data
    {MUTATION_RESULT_FIELDS}
  }}
}}
"""

_GET_AUTHENTICATED_USER_ID_MUTATION = "mutation { getAuthenticatedUserId { id } }"


#: Accepted input for dates and times: a datetime (naive means UTC), a date
#: (00:00 UTC), unix seconds, or an ISO 8601 string such as "2026-09-21".
type TimeInput = datetime | date | float | int | str


def to_utc_datetime(value: TimeInput) -> datetime:
    """Convert a `TimeInput` into an aware UTC datetime.

    A naive `datetime` (or an ISO string without an offset) is treated as UTC.
    A `date` (or a date-only ISO string) becomes 00:00 UTC of that day.

    Args:
        value: The value to convert.

    Returns:
        A timezone-aware `datetime`.

    """
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return datetime.fromtimestamp(float(value), tz=UTC)


def to_timestamp(value: TimeInput) -> float:
    """Convert a datetime, date, or number into unix seconds, as the API expects.

    Args:
        value: The value to convert (see `to_utc_datetime`).

    Returns:
        Unix seconds as a float.

    """
    if isinstance(value, int | float):
        return float(value)
    return to_utc_datetime(value).timestamp()


def now_timestamp() -> float:
    """Return the current time as unix seconds.

    Returns:
        Unix seconds as a float.

    """
    return datetime.now(tz=UTC).timestamp()


def default_due_date(days: int) -> date:
    """Return the date `days` days after today's UTC date.

    Args:
        days: The number of days to add.

    Returns:
        The due date (sent as 00:00 UTC by `to_timestamp`).

    """
    return datetime.now(tz=UTC).date() + timedelta(days=days)


def compact(**fields: Any) -> dict[str, Any]:
    """Build a dict from keyword arguments, dropping `None` values.

    Args:
        **fields: The candidate fields.

    Returns:
        The fields whose value is not `None`.

    """
    return {key: value for key, value in fields.items() if value is not None}


def prepare_note_text(text: str) -> str:
    """Escape plain text for Etherpad's `setHTML`, as `CreateNote` expects.

    Args:
        text: The plain text to store.

    Returns:
        HTML-escaped text with newlines turned into `<br>`.

    """
    return html.escape(text).replace("\n", "<br>")


def extract_notes(data: dict[str, Any]) -> str | None:
    """Extract plain description text from the `NOTES_FIELDS` projection.

    Selecting `notesText` without `collaborationEnabled` makes the API resolve
    it to `""`, so both must be selected.

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


def merge_nodes(*node_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge raw GraphQL node lists, deduping by id and sorting by creation date.

    Combines connections selected conditionally in one document (e.g. `issues`
    plus `recentlySolvedIssues`), which are each ordered but not combined.

    Args:
        *node_lists: Raw node lists to merge, in any order.

    Returns:
        The merged nodes with each id appearing once (first occurrence
        wins), sorted by `(dateCreated, id)`.

    """
    seen: dict[int, dict[str, Any]] = {}
    for nodes in node_lists:
        for node in nodes:
            seen.setdefault(node["id"], node)
    return sorted(seen.values(), key=lambda node: (node["dateCreated"], node["id"]))


def _dig(data: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
    """Walk nested dict keys, returning `None` as soon as a level is missing.

    Returns:
        The value found at the end of `keys`, or `None`.

    """
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = cast("dict[str, Any]", current).get(key)
    return current


def dig_nodes(data: dict[str, Any] | None, *keys: str) -> list[dict[str, Any]]:
    """Walk nested dict keys and read the `nodes` list of the connection there.

    Args:
        data: The raw GraphQL `data` object (or a nested object within it).
        *keys: The nested keys leading to the connection.

    Returns:
        The connection's nodes, or an empty list if any level is missing or
        `null`.

    """
    connection = _dig(data, keys)
    if not isinstance(connection, dict):
        return []
    nodes = cast("dict[str, Any]", connection).get("nodes")
    return list(nodes) if nodes else []


class UserIdCache:
    """The authenticated user's id, shared by every operations object of a client."""

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self.user_id: int | None = None
        self.lock = asyncio.Lock()


class AbstractGraphQLOperations(AbstractOperations):
    """Shared, transport-agnostic logic for v2 (GraphQL) operations."""

    def __init__(
        self, client: Any, graphql_url: str, user_id_cache: UserIdCache | None = None
    ) -> None:
        """Initialize the operations class.

        Args:
            client: The httpx client (sync or async) to use for requests.
            graphql_url: The absolute URL of the GraphQL endpoint.
            user_id_cache: The client's shared current-user cache. A new,
                unshared cache is created when omitted.

        """
        super().__init__(client)
        self._graphql_url = graphql_url
        self._user_id_cache = user_id_cache or UserIdCache()

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

        A JSON body without an `errors` array still goes through
        `raise_for_status()`, so a non-2xx status (e.g. an expired-token 401)
        raises `httpx.HTTPStatusError` instead of returning empty `data`.

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
    ) -> dict[str, Any]:
        """Check a mutation result object and return it.

        Args:
            result: The mutation's result object (e.g. `data["EditIssue"]`).
            action: A short description of the mutation, used in error
                messages (e.g. `"create issue"`).

        Returns:
            `result`, unchanged.

        Raises:
            GraphQLError: If `result` is missing, has a falsy `success`, or
                has an `id` of `0`.

        """
        if not result:
            raise GraphQLError(f"{action} failed: no result returned")
        if "success" in result and not result["success"]:
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
        if "id" in result and not result["id"]:
            raise GraphQLError(f"{action} failed: no id returned")
        return result

    @staticmethod
    def _one(
        data: dict[str, Any], *path: str, label: str, entity_id: int
    ) -> dict[str, Any]:
        """Read the single entity at `path`, or raise if it is missing.

        A by-id query returns `null` rather than a GraphQL error for an unknown
        or invisible id. When `path` ends at a connection or list, its first
        node is returned.

        Args:
            data: The raw GraphQL `data` object.
            *path: The nested keys leading to the entity.
            label: A human-readable entity label (e.g. `"Issue"`).
            entity_id: The requested id, used in the error message.

        Returns:
            The entity object.

        Raises:
            GraphQLError: If the entity is missing, `null`, or an empty list.

        """
        found = _dig(data, path)
        if isinstance(found, dict) and "nodes" in found:
            found = cast("dict[str, Any]", found)["nodes"]
        if isinstance(found, list):
            nodes = cast("list[Any]", found)
            found = nodes[0] if nodes else None
        if not isinstance(found, dict) or not found:
            raise GraphQLError(f"{label} {entity_id} not found")
        return cast("dict[str, Any]", found)


class GraphQLOperations(AbstractGraphQLOperations):
    """Sync base class for v2 (GraphQL) operation classes."""

    _client: httpx.Client

    @property
    def user_id(self) -> int:
        """Get the current user's ID, fetching it if needed.

        Returns:
            The user ID of the authenticated user.

        """
        cache = self._user_id_cache
        if cache.user_id is None:
            data = self._execute(_GET_AUTHENTICATED_USER_ID_MUTATION)
            cache.user_id = int(data["getAuthenticatedUserId"]["id"])
        return cache.user_id

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

    def _mutate(
        self,
        query: str,
        variables: dict[str, Any] | None,
        *,
        root_field: str,
        action: str,
    ) -> dict[str, Any]:
        """Execute a mutation and return its checked result object.

        A result shaped `{success ...}` must succeed and a result with an `id`
        must have a non-zero id, since the API reports some failures that way
        instead of through `errors`.

        Args:
            query: The GraphQL mutation document.
            variables: The GraphQL variables for the document.
            root_field: The mutation's root field in `data` (e.g. `EditIssue`).
            action: A short description of the mutation, used in error messages.

        Returns:
            The mutation's result object (`data[root_field]`). See
            `_check_mutation_result` for the errors this can raise.

        """
        data = self._execute(query, variables)
        return self._check_mutation_result(data.get(root_field), action=action)

    def _create_note(self, text: str) -> str:
        """Create a new Etherpad note pad from plain text.

        Args:
            text: The plain text to store (escaped for Etherpad here).

        Returns:
            The new pad's id, for use as `notesId` on a create/edit input.

        """
        result = self._mutate(
            _CREATE_NOTE_MUTATION,
            {"text": prepare_note_text(text)},
            root_field="CreateNote",
            action="create note",
        )
        return str(result["data"])

    def _notes_input(self, notes: str | None) -> dict[str, Any]:
        """Build the notes fields of a create/edit input, creating the pad.

        Args:
            notes: The description text, or `None` to leave notes unchanged.

        Returns:
            `{}` when `notes` is `None`, else `notesId`/`collaborationEnabled`.

        """
        if notes is None:
            return {}
        return {"notesId": self._create_note(notes), "collaborationEnabled": True}


class AsyncGraphQLOperations(AbstractGraphQLOperations):
    """Async base class for v2 (GraphQL) operation classes."""

    _client: httpx.AsyncClient

    @property
    def user_id(self) -> int:
        """Get the cached user ID.

        For async operations, use `get_user_id()` to fetch from the API.

        Raises:
            RuntimeError: If the user ID has not been fetched yet.

        """
        user_id = self._user_id_cache.user_id
        if user_id is None:
            raise RuntimeError("User ID not set. Use get_user_id() to fetch from API.")
        return user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        """Set the cached user ID."""
        self._user_id_cache.user_id = value

    async def get_user_id(self) -> int:
        """Get the current user's ID, fetching it once per client if needed.

        Returns:
            The user ID of the authenticated user.

        """
        cache = self._user_id_cache
        if cache.user_id is None:
            async with cache.lock:
                if cache.user_id is None:
                    data = await self._execute(_GET_AUTHENTICATED_USER_ID_MUTATION)
                    cache.user_id = int(data["getAuthenticatedUserId"]["id"])
        return cache.user_id

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

    async def _mutate(
        self,
        query: str,
        variables: dict[str, Any] | None,
        *,
        root_field: str,
        action: str,
    ) -> dict[str, Any]:
        """Execute a mutation and return its checked result object.

        See `GraphQLOperations._mutate`.

        Args:
            query: The GraphQL mutation document.
            variables: The GraphQL variables for the document.
            root_field: The mutation's root field in `data` (e.g. `EditIssue`).
            action: A short description of the mutation, used in error messages.

        Returns:
            The mutation's result object (`data[root_field]`).

        """
        data = await self._execute(query, variables)
        return self._check_mutation_result(data.get(root_field), action=action)

    async def _create_note(self, text: str) -> str:
        """Create a new Etherpad note pad from plain text.

        Args:
            text: The plain text to store (escaped for Etherpad here).

        Returns:
            The new pad's id, for use as `notesId` on a create/edit input.

        """
        result = await self._mutate(
            _CREATE_NOTE_MUTATION,
            {"text": prepare_note_text(text)},
            root_field="CreateNote",
            action="create note",
        )
        return str(result["data"])

    async def _notes_input(self, notes: str | None) -> dict[str, Any]:
        """Build the notes fields of a create/edit input, creating the pad.

        Args:
            notes: The description text, or `None` to leave notes unchanged.

        Returns:
            `{}` when `notes` is `None`, else `notesId`/`collaborationEnabled`.

        """
        if notes is None:
            return {}
        return {
            "notesId": await self._create_note(notes),
            "collaborationEnabled": True,
        }
