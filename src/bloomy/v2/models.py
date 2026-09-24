"""Pydantic models for the Bloomy v2 (GraphQL) API.

Conventions for v2 models:

- Aliases are the camelCase GraphQL field names; operations build every model
  with `Model.model_validate` on the raw GraphQL object.
- Owners and related entities are nested refs: `owner: UserRef | None`
  (aliased from `assignee`, which can be `null`) and `meeting: MeetingRef |
  None`, never flattened ids/names.
- Datetimes use the `_date` suffix and are timezone-aware UTC `datetime`
  objects, converted from the API's unix-seconds floats.
- `notes` is the plain description text, computed from the `NOTES_FIELDS`
  projection (see `bloomy.v2.base.extract_notes`); `notes_id` is the pad id
  needed to update it.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, cast

from pydantic import (
    AliasChoices,
    AliasPath,
    BeforeValidator,
    Field,
    model_validator,
)

from ..models import BloomyBaseModel, OptionalFloat
from .base import extract_notes, to_utc_datetime


def _parse_gql_datetime(value: Any) -> datetime | None:
    """Convert a GraphQL unix-seconds timestamp into an aware UTC datetime.

    Returns:
        The converted datetime, or `None` if `value` is `None`.

    """
    return None if value is None else to_utc_datetime(value)


def _connection_nodes(value: Any) -> Any:
    """Unwrap a GraphQL connection (`{"nodes": [...]}`) into its node list.

    Returns:
        The node list (`[]` for `null`), or `value` unchanged if it is not a
        connection object.

    """
    if value is None:
        return []
    if isinstance(value, dict):
        return cast("dict[str, Any]", value).get("nodes") or []
    return value


def _raw_dict(data: Any) -> dict[str, Any] | None:
    """Narrow a `mode="before"` validator's input to a raw GraphQL object.

    Returns:
        `data` if it is a dict, else `None`.

    """
    return cast("dict[str, Any]", data) if isinstance(data, dict) else None


# Reusable annotated types for the v2 API's unix-seconds timestamps.
type GqlDatetime = Annotated[datetime, BeforeValidator(_parse_gql_datetime)]
type GqlOptionalDatetime = Annotated[
    datetime | None, BeforeValidator(_parse_gql_datetime)
]
# A nested connection (`field { nodes { ... } }`), validated as a plain list.
type Connection[T] = Annotated[list[T], BeforeValidator(_connection_nodes)]


class GqlBaseModel(BloomyBaseModel):
    """Base model for v2 entities, validated from raw GraphQL objects.

    Fields validate by alias (the raw GraphQL key) or by field name, so
    `Model.model_validate(model.model_dump())` round-trips.
    """

    @model_validator(mode="before")
    @classmethod
    def _fill_notes(cls, data: Any) -> Any:
        """Compute `notes` when the raw object carries the `NOTES_FIELDS`.

        Returns:
            The raw object, with `notes` added when applicable.

        """
        raw = _raw_dict(data)
        if raw is not None and "collaborationEnabled" in raw:
            return {**raw, "notes": extract_notes(raw)}
        return data


class UserRef(GqlBaseModel):
    """Minimal reference to a user, as nested inside other v2 entities.

    This is what GraphQL `assignee { id fullName }` projections return; use
    `User` for the full `user`/`users` query result.
    """

    id: int
    full_name: str | None = Field(default=None, alias="fullName")


class MeetingRef(GqlBaseModel):
    """Minimal reference to a meeting, as nested inside other v2 entities.

    This is what GraphQL `meeting { id name }` projections return; use
    `Meeting` for the full `meeting` query result.
    """

    id: int
    name: str | None = None


class User(GqlBaseModel):
    """Model for a full v2 user, from the `user`/`users` queries."""

    id: int
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    full_name: str | None = Field(default=None, alias="fullName")
    email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("email", AliasPath("user", "email")),
    )
    avatar: str | None = None


class MeetingListItem(GqlBaseModel):
    """Model for a meeting list item, from `user(id){ meetingsListLookup }`."""

    id: int
    name: str | None = None
    meeting_type: str | None = Field(default=None, alias="meetingType")
    created_date: GqlDatetime = Field(alias="createdTimestamp")
    archived: bool = False
    user_is_attendee: bool = Field(default=False, alias="userIsAttendee")
    is_current_user_admin: bool = Field(default=False, alias="isCurrentUserAdmin")


class Meeting(GqlBaseModel):
    """Model for full meeting details, from the `meeting(id)` query."""

    id: int
    name: str | None = None
    org_id: int | None = Field(default=None, alias="orgId")
    meeting_type: str | None = Field(default=None, alias="meetingType")
    created_date: GqlDatetime = Field(alias="createdTimestamp")
    archived: bool = False
    attendees: Connection[User] = Field(default_factory=list)


class Issue(GqlBaseModel):
    """Model for an issue, from the `issue(id)`/`meeting(id){ issues }` queries."""

    id: int
    title: str | None = None
    owner: UserRef | None = Field(default=None, alias="assignee")
    meeting: MeetingRef | None = None
    recurrence_id: int | None = Field(default=None, alias="recurrenceId")
    long_term: bool = Field(default=False, alias="addToDepartmentPlan")
    notes_id: str | None = Field(default=None, alias="notesId")
    notes: str | None = None
    completed: bool = False
    completed_date: GqlOptionalDatetime = Field(
        default=None, alias="completedTimestamp"
    )
    archived: bool = False
    archived_date: GqlOptionalDatetime = Field(default=None, alias="archivedTimestamp")
    created_date: GqlDatetime = Field(alias="dateCreated")
    priority_vote_rank: int | None = Field(default=None, alias="priorityVoteRank")
    num_star_votes: int = Field(default=0, alias="numStarVotes")
    issue_number: int | None = Field(default=None, alias="issueNumber")

    @model_validator(mode="before")
    @classmethod
    def _long_term_is_not_archived(cls, data: Any) -> Any:
        """Report a long-term issue as not archived.

        The API stores every long-term issue as archived, while the web app
        lists them on the Long-Term tab; archiving a long-term issue clears
        `addToDepartmentPlan`, so it then counts as archived.

        Returns:
            The raw object, with `archived` cleared for a long-term issue.

        """
        raw = _raw_dict(data)
        if raw is not None and raw.get("addToDepartmentPlan"):
            return {**raw, "archived": False}
        return data


class Headline(GqlBaseModel):
    """Model for a headline, from `headline(id)`/`meeting(id){ headlines }` queries."""

    id: int
    title: str | None = None
    owner: UserRef | None = Field(default=None, alias="assignee")
    meeting: MeetingRef | None = None
    recurrence_id: int | None = Field(default=None, alias="recurrenceId")
    notes_id: str | None = Field(default=None, alias="notesId")
    notes: str | None = None
    archived: bool = False
    archived_date: GqlOptionalDatetime = Field(default=None, alias="archivedTimestamp")
    created_date: GqlDatetime = Field(alias="dateCreated")


class Todo(GqlBaseModel):
    """Model for a to-do, from the `todo(id)` query and the to-do list queries."""

    id: int
    title: str | None = None
    owner: UserRef | None = Field(default=None, alias="assignee")
    meeting: MeetingRef | None = None
    due_date: GqlOptionalDatetime = Field(default=None, alias="dueDate")
    completed: bool = False
    completed_date: GqlOptionalDatetime = Field(
        default=None, alias="completedTimestamp"
    )
    archived: bool = False
    archived_date: GqlOptionalDatetime = Field(default=None, alias="archivedTimestamp")
    created_date: GqlDatetime = Field(alias="dateCreated")
    notes_id: str | None = Field(default=None, alias="notesId")
    notes: str | None = None


class GoalStatus(StrEnum):
    """Status of a v2 goal (rock), matching the GraphQL API's `gqlGoalStatus` values.

    Distinct from `bloomy.models.GoalStatus` (v1's REST enum), whose values
    (`on`, `off`, `complete`) do not match these.
    """

    ON_TRACK = "ON_TRACK"
    OFF_TRACK = "OFF_TRACK"
    COMPLETED = "COMPLETED"


class Milestone(GqlBaseModel):
    """Model for a goal milestone, from `goal(id){ milestones }`.

    There is no root `milestone(id)` query in the GraphQL API: a milestone is
    only reachable through its parent goal (`goal_id`).
    """

    id: int
    goal_id: int = Field(alias="goalId")
    title: str | None = None
    due_date: GqlDatetime = Field(alias="dueDate")
    completed: bool = False
    status: str | None = None
    created_date: GqlOptionalDatetime = Field(default=None, alias="dateCreated")


class Goal(GqlBaseModel):
    """Model for a goal (rock), from the `goal(id)`/`goals(userId)` queries."""

    id: int
    title: str | None = None
    status: GoalStatus = GoalStatus.ON_TRACK
    owner: UserRef | None = Field(default=None, alias="assignee")
    due_date: GqlOptionalDatetime = Field(default=None, alias="dueDate")
    archived: bool = False
    archived_date: GqlOptionalDatetime = Field(default=None, alias="archivedTimestamp")
    created_date: GqlDatetime = Field(alias="dateCreated")
    notes_id: str | None = Field(default=None, alias="notesId")
    notes: str | None = None
    milestones: Connection[Milestone] = Field(default_factory=list)
    meetings: Connection[MeetingRef] = Field(default_factory=list)


class MetricUnit(StrEnum):
    """Display unit for a v2 metric's scores, matching `gqlUnitType`."""

    NONE = "NONE"
    DOLLAR = "DOLLAR"
    PERCENT = "PERCENT"
    POUND = "POUND"
    EUROS = "EUROS"
    PESOS = "PESOS"
    YEN = "YEN"
    YESNO = "YESNO"
    INR = "INR"
    DIRHAM = "DIRHAM"
    RAND = "RAND"
    XCG = "XCG"


class MetricRule(StrEnum):
    """Comparison rule between a v2 metric's score and its goal.

    Matches the GraphQL API's `gqlLessGreater` values.

    Symbols: `GREATER_THAN` = `>=`, `GREATER_THAN_NOT_EQUAL` = `>`,
    `LESS_THAN` = `<`, `LESS_THAN_OR_EQUAL` = `<=`, `EQUAL_TO` = `==`,
    `BETWEEN` = `min_goal <= score <= max_goal`.
    """

    EQUAL_TO = "EQUAL_TO"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_NOT_EQUAL = "GREATER_THAN_NOT_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    BETWEEN = "BETWEEN"


class MetricFrequency(StrEnum):
    """Scoring cadence for a v2 metric, matching `gqlMetricFrequency`."""

    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    DAILY = "DAILY"


class Metric(GqlBaseModel):
    """Model for a metric (KPI), from the `metric(id)`/`meeting(id){ metrics }` queries.

    `id` is always the Measurable id (aliased from `measurableId`). On
    `meeting(id){ metrics }` the raw `id` field is instead a meeting-link id
    (not the metric id), so this SDK never selects it -- see
    `bloomy.v2.operations.metric`.
    """

    id: int = Field(alias="measurableId")
    title: str | None = None
    owner: UserRef | None = Field(default=None, alias="assignee")
    units: MetricUnit
    rule: MetricRule
    frequency: MetricFrequency
    goal: OptionalFloat = Field(default=None, alias="singleGoalValue")
    min_goal: OptionalFloat = Field(default=None, alias="minGoalValue")
    max_goal: OptionalFloat = Field(default=None, alias="maxGoalValue")
    archived: bool = False
    created_date: GqlDatetime = Field(alias="dateCreated")
    notes_id: str | None = Field(default=None, alias="notesId")
    notes: str | None = None
    is_externally_synced: bool = Field(default=False, alias="isExternallySynced")


class MetricScore(GqlBaseModel):
    """Model for a metric score, from `metric(id){ scoresNonPaginated }`.

    There is no root `score(id)` query: a score is only reachable through
    its parent metric (`metric_id`).
    """

    id: int
    metric_id: int = Field(alias="measurableId")
    value: OptionalFloat = None
    week_date: GqlOptionalDatetime = Field(default=None, alias="timestamp")
    notes: Annotated[str | None, BeforeValidator(lambda value: value or None)] = Field(
        default=None, validation_alias="notesText"
    )
