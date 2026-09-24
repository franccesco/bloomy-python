"""Pydantic models for the Bloomy v2 (GraphQL) API.

Conventions (apply these uniformly to models added for other v2 entities —
headline, todo, goal, milestone, metric):

- **Aliases are camelCase**, matching the GraphQL field names verbatim
  (`Field(alias="dateCreated")`), unlike v1's PascalCase REST aliases. Since
  GraphQL response shapes already map ~1:1 onto these models, operation
  mixins build most models by spreading the raw response dict as keyword
  arguments (`Model(**data, notes=computed_notes)`), relying on
  `BloomyBaseModel`'s `validate_by_alias=True` to do the field mapping and
  on Pydantic's default `extra="ignore"` to drop unmapped raw keys (e.g.
  `notesText`, `collaborationEnabled`). This works cleanly for `Issue`
  (see `IssueOperationsMixin._transform_issue`), whose fields all come from
  one flat response object. Where a mixin instead reshapes a nested
  connection by hand (e.g. `Meeting.attendees`, or flattening a nested
  `user { email }` onto `User`, in `MeetingOperationsMixin._transform_*`),
  construct the model with **alias keyword names**
  (`User(firstName=..., fullName=...)`), not the snake_case field names:
  Pydantic's generated `__init__` exposes the alias — not the field name —
  to static type checkers whenever `Field(alias=...)` is set, even though
  `validate_by_name=True` also accepts the field name at runtime. Mixing the
  two (spreading a raw dict vs. hand-building kwargs) is fine; mixing
  aliases and field names *within one call* is not checked by pydantic and
  will silently pass `None`/defaults for the field-name-spelled arguments.
- **Owners are nested refs**: an entity's assignee is exposed as
  `owner: UserRef | None` (aliased from the GraphQL `assignee` field), never
  flattened into `owner_id`/`owner_name`. `owner` is optional because
  `assignee` can be `null` (e.g. unowned issues).
- **Related entities are nested refs** too: an `Issue`'s parent meeting is
  `meeting: MeetingRef | None` (aliased from GraphQL `meeting`), not
  flattened `meeting_id`/`meeting_name`. Reuse `MeetingRef`/`UserRef` for
  this rather than inventing new ref types per entity.
- **Datetimes use the `_date` suffix** (`created_date`, `due_date`,
  `completed_date`, `archived_date`) and are always timezone-aware UTC
  `datetime` objects, converted from the API's unix-seconds floats via the
  `GqlDatetime`/`GqlOptionalDatetime` annotated types. This mirrors v1's
  `_date` naming and lines up with the public API's `due_date` parameters.
- **Notes**: description text is exposed as `notes: str | None`, computed by
  `bloomy.v2.base.extract_notes` from the raw
  `notesText`/`localHtml`/`collaborationEnabled` projection. `notes_id` is
  kept alongside it (aliased from `notesId`) since it is needed to update
  the description later (see `v2/base.py`).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BeforeValidator, Field

from ..models import BloomyBaseModel, OptionalFloat


def _parse_gql_datetime(value: Any) -> datetime | None:
    """Convert a GraphQL unix-seconds timestamp into a timezone-aware datetime.

    Returns:
        The converted datetime, or `None` if `value` is `None`.

    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    return datetime.fromtimestamp(float(value), tz=UTC)


# Reusable annotated types for the v2 API's unix-seconds timestamps.
type GqlDatetime = Annotated[datetime, BeforeValidator(_parse_gql_datetime)]
type GqlOptionalDatetime = Annotated[
    datetime | None, BeforeValidator(_parse_gql_datetime)
]


class UserRef(BloomyBaseModel):
    """Minimal reference to a user, as nested inside other v2 entities.

    This is what GraphQL `assignee { id fullName }` projections return; use
    `User` for the full `user`/`users` query result.
    """

    id: int
    full_name: str | None = Field(default=None, alias="fullName")


class MeetingRef(BloomyBaseModel):
    """Minimal reference to a meeting, as nested inside other v2 entities.

    This is what GraphQL `meeting { id name }` projections return; use
    `Meeting` for the full `meeting` query result.
    """

    id: int
    name: str | None = None


class User(BloomyBaseModel):
    """Model for a full v2 user, from the `user`/`users` queries."""

    id: int
    first_name: str | None = Field(default=None, alias="firstName")
    last_name: str | None = Field(default=None, alias="lastName")
    full_name: str | None = Field(default=None, alias="fullName")
    email: str | None = None
    avatar: str | None = None


class MeetingListItem(BloomyBaseModel):
    """Model for a meeting list item, from `user(id){ meetingsListLookup }`."""

    id: int
    name: str | None = None
    meeting_type: str | None = Field(default=None, alias="meetingType")
    created_date: GqlDatetime = Field(alias="createdTimestamp")
    archived: bool = False
    user_is_attendee: bool = Field(default=False, alias="userIsAttendee")
    is_current_user_admin: bool = Field(default=False, alias="isCurrentUserAdmin")


class Meeting(BloomyBaseModel):
    """Model for full meeting details, from the `meeting(id)` query."""

    id: int
    name: str | None = None
    org_id: int | None = Field(default=None, alias="orgId")
    meeting_type: str | None = Field(default=None, alias="meetingType")
    created_date: GqlDatetime = Field(alias="createdTimestamp")
    archived: bool = False
    attendees: list[User] = Field(default_factory=list)


class Issue(BloomyBaseModel):
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


class Headline(BloomyBaseModel):
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


class Todo(BloomyBaseModel):
    """Model for a to-do, from the `todo(id)`/`meeting(id){ todos }` queries."""

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


class Milestone(BloomyBaseModel):
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


class Goal(BloomyBaseModel):
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
    milestones: list[Milestone] = Field(default_factory=list)
    meetings: list[MeetingRef] = Field(default_factory=list)


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


class Metric(BloomyBaseModel):
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


class MetricScore(BloomyBaseModel):
    """Model for a metric score, from `metric(id){ scoresNonPaginated }`.

    There is no root `score(id)` query: a score is only reachable through
    its parent metric (`metric_id`).
    """

    id: int
    metric_id: int = Field(alias="measurableId")
    value: OptionalFloat = None
    week_date: GqlOptionalDatetime = Field(default=None, alias="timestamp")
    notes: str | None = None
