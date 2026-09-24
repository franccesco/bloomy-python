# v2: The GraphQL API

The SDK talks to two different Bloom Growth APIs, both reachable from the same
`Client`/`AsyncClient` instance:

- **`client.v1`** — the REST API at `/api/v1`. This is the API the SDK has
  always exposed. Nothing about it changed.
- **`client.v2`** — the GraphQL API at `/graphql/`. It covers the same
  entities (users, meetings, issues, headlines, todos, goals, milestones,
  metrics) through a different transport, with some behavior that does not
  match v1 one-to-one.

This guide explains how the two fit together, tours every `client.v2`
namespace and method, and covers the behavior that is specific to v2:
description ("notes") handling, archive/delete semantics per entity, metric
score/week semantics, and `GraphQLError`.

## v1 vs v2

### v1 (REST, unchanged)

`client.v1.user`, `client.v1.meeting`, `client.v1.todo`, `client.v1.goal`,
`client.v1.scorecard`, `client.v1.issue`, and `client.v1.headline` are the
same operation classes the SDK has always had. The top-level attributes you
may already be using — `client.user`, `client.meeting`, `client.todo`, and so
on — are aliases pointing at the exact same objects as `client.v1.*`, kept for
backward compatibility:

```python
from bloomy import Client

client = Client(api_key="your-api-key")

client.meeting.list() is client.v1.meeting.list  # same bound method, same instance
client.meeting is client.v1.meeting              # True
```

Existing code that uses `client.user`, `client.meeting.create()`, and so on
keeps working exactly as before. See the [Basic Usage](usage.md) guide and the
[v1 API Reference](../api/operations/users.md) for those operations.

### v2 (GraphQL, new)

`client.v2.user`, `client.v2.meeting`, `client.v2.issue`, `client.v2.headline`,
`client.v2.todo`, `client.v2.goal`, `client.v2.milestone`, and
`client.v2.metric` are new operation classes that send GraphQL documents
instead of REST requests. They:

- Use the **same API key** and the **same underlying HTTP client** as v1 — no
  separate authentication step. A v2 request posts to an absolute URL, which
  overrides the client's `base_url` for that one request.
- Default their GraphQL endpoint to the scheme and host of `base_url` plus
  `/graphql/` (e.g. `https://app.bloomgrowth.com/graphql/`). Pass
  `graphql_url` explicitly if your GraphQL endpoint lives somewhere else:

```python
from bloomy import Client

client = Client(
    api_key="your-api-key",
    graphql_url="https://app.bloomgrowth.com/graphql/",
)

client.v2.meeting.details(123)
```

- Return the **same kind of Pydantic models** as v1 (typed, IDE-friendly), but
  the models themselves are different classes (`bloomy.v2.models.Issue`, not
  `bloomy.models.IssueDetails`) with different fields. See
  [Models](../api/v2/models.md) for the field-naming conventions.
- Raise `GraphQLError` (a subclass of `APIError`) instead of a plain
  `APIError` for failed requests. See [GraphQLError](#graphqlerror) below.

=== "Sync"

    ```python
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # v1 (REST) — unchanged
        meetings = client.meeting.list()

        # v2 (GraphQL) — new
        meeting = client.v2.meeting.details(meetings[0].id)
        issues = client.v2.issue.list(meeting.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # v1 (REST) — unchanged
            meetings = await client.meeting.list()

            # v2 (GraphQL) — new
            meeting = await client.v2.meeting.details(meetings[0].id)
            issues = await client.v2.issue.list(meeting.id)

    asyncio.run(main())
    ```

v1 and v2 can be mixed freely in the same script: they share one client, one
API key, and one connection pool.

## Quick tour of `client.v2`

Every namespace below exposes a sync class (`client.v2.<name>`) and an async
mirror with identical method signatures (`await`ed). Full parameter and
return-type documentation lives on each entity's API reference page.

| Namespace | Sync class | Async class | Model(s) |
|---|---|---|---|
| `client.v2.user` | `UserOperations` | `AsyncUserOperations` | [`User`](../api/v2/models.md#bloomy.v2.models.User) |
| `client.v2.meeting` | `MeetingOperations` | `AsyncMeetingOperations` | [`Meeting`](../api/v2/models.md#bloomy.v2.models.Meeting), [`MeetingListItem`](../api/v2/models.md#bloomy.v2.models.MeetingListItem) |
| `client.v2.issue` | `IssueOperations` | `AsyncIssueOperations` | [`Issue`](../api/v2/models.md#bloomy.v2.models.Issue) |
| `client.v2.headline` | `HeadlineOperations` | `AsyncHeadlineOperations` | [`Headline`](../api/v2/models.md#bloomy.v2.models.Headline) |
| `client.v2.todo` | `TodoOperations` | `AsyncTodoOperations` | [`Todo`](../api/v2/models.md#bloomy.v2.models.Todo) |
| `client.v2.goal` | `GoalOperations` | `AsyncGoalOperations` | [`Goal`](../api/v2/models.md#bloomy.v2.models.Goal), [`Milestone`](../api/v2/models.md#bloomy.v2.models.Milestone) |
| `client.v2.milestone` | `MilestoneOperations` | `AsyncMilestoneOperations` | [`Milestone`](../api/v2/models.md#bloomy.v2.models.Milestone) |
| `client.v2.metric` | `MetricOperations` | `AsyncMetricOperations` | [`Metric`](../api/v2/models.md#bloomy.v2.models.Metric), [`MetricScore`](../api/v2/models.md#bloomy.v2.models.MetricScore) |

### `client.v2.user`

| Method | Signature | Description |
|---|---|---|
| `details()` | `details(user_id=None) -> User` | Get a user. Defaults to the current user. |
| `list()` | `list() -> list[User]` | List every user in the organization. |

### `client.v2.meeting`

| Method | Signature | Description |
|---|---|---|
| `list()` | `list(user_id=None) -> list[MeetingListItem]` | List meetings a user attends. Defaults to the current user. |
| `details()` | `details(meeting_id) -> Meeting` | Get a meeting, including its attendees. |
| `attendees()` | `attendees(meeting_id) -> list[User]` | List a meeting's attendees. |

### `client.v2.issue`

| Method | Signature | Description |
|---|---|---|
| `details()` | `details(issue_id) -> Issue` | Get an issue. |
| `list()` | `list(meeting_id, *, long_term=False, include_solved=False, include_archived=False) -> list[Issue]` | List a meeting's issues. |
| `create()` | `create(meeting_id, title, user_id=None, notes=None, long_term=False) -> Issue` | Create an issue. |
| `update()` | `update(issue_id, *, title=None, user_id=None, notes=None, long_term=None, meeting_id=None) -> Issue` | Update an issue. |
| `solve()` | `solve(issue_id) -> Issue` | Mark an issue as solved. |
| `reopen()` | `reopen(issue_id) -> Issue` | Reopen a solved issue. |
| `archive()` | `archive(issue_id) -> Issue` | Archive an issue. |
| `restore()` | `restore(issue_id) -> Issue` | Restore an archived (short-term) issue. |

### `client.v2.headline`

| Method | Signature | Description |
|---|---|---|
| `details()` | `details(headline_id) -> Headline` | Get a headline. |
| `list()` | `list(meeting_id=None, user_id=None, include_archived=False) -> list[Headline]` | List headlines for a meeting or a user (mutually exclusive). |
| `create()` | `create(meeting_id, title, user_id=None, notes=None) -> Headline` | Create a headline. |
| `update()` | `update(headline_id, *, title=None, user_id=None, notes=None) -> Headline` | Update a headline. |
| `archive()` | `archive(headline_id) -> Headline` | Archive a headline. |
| `restore()` | `restore(headline_id) -> Headline` | Restore an archived headline. |

### `client.v2.todo`

| Method | Signature | Description |
|---|---|---|
| `details()` | `details(todo_id) -> Todo` | Get a to-do. |
| `list()` | `list(meeting_id=None, user_id=None, *, include_completed=False, include_archived=False) -> list[Todo]` | List to-dos for a meeting or a user (mutually exclusive). |
| `create()` | `create(title, meeting_id=None, user_id=None, due_date=None, notes=None) -> Todo` | Create a to-do. Omit `meeting_id` for a personal to-do. |
| `update()` | `update(todo_id, *, title=None, due_date=None, user_id=None, notes=None) -> Todo` | Update a to-do. |
| `complete()` | `complete(todo_id) -> Todo` | Mark a to-do as complete. |
| `reopen()` | `reopen(todo_id) -> Todo` | Reopen a completed to-do. |
| `archive()` | `archive(todo_id) -> Todo` | Archive a to-do. |
| `restore()` | `restore(todo_id) -> Todo` | Restore an archived to-do. |

### `client.v2.goal`

| Method | Signature | Description |
|---|---|---|
| `list()` | `list(meeting_id=None, user_id=None, *, include_archived=False) -> list[Goal]` | List goals for a meeting or a user (mutually exclusive). |
| `details()` | `details(goal_id) -> Goal` | Get a goal, including its milestones. |
| `create()` | `create(meeting_id, title, user_id=None, due_date=None, status=GoalStatus.ON_TRACK, notes=None, milestones=None) -> Goal` | Create a goal, optionally with milestones. |
| `update()` | `update(goal_id, *, title=None, status=None, due_date=None, user_id=None, notes=None) -> Goal` | Update a goal. |
| `archive()` | `archive(goal_id) -> Goal` | Archive a goal. |
| `restore()` | `restore(goal_id) -> Goal` | Restore an archived goal. |

### `client.v2.milestone`

| Method | Signature | Description |
|---|---|---|
| `list()` | `list(goal_id) -> list[Milestone]` | List a goal's milestones. |
| `create()` | `create(goal_id, title, due_date, completed=False) -> Milestone` | Create a milestone on a goal. |
| `update()` | `update(milestone_id, goal_id, *, title=None, due_date=None, completed=None) -> Milestone` | Update a milestone. Requires `goal_id` — see [below](#archive-vs-delete-semantics-per-entity). |
| `complete()` | `complete(milestone_id, goal_id) -> Milestone` | Mark a milestone as completed. Requires `goal_id`. |
| `delete()` | `delete(milestone_id) -> None` | Delete a milestone. No `goal_id` needed. |

### `client.v2.metric`

| Method | Signature | Description |
|---|---|---|
| `details()` | `details(metric_id) -> Metric` | Get a metric. |
| `list()` | `list(meeting_id=None, user_id=None, frequency=None) -> list[Metric]` | List metrics for a meeting or a user (mutually exclusive). |
| `create()` | `create(meeting_id, title, user_id=None, goal=None, units=MetricUnit.NONE, rule=MetricRule.GREATER_THAN, frequency=MetricFrequency.WEEKLY, min_goal=None, max_goal=None, notes=None) -> Metric` | Create a metric. |
| `update()` | `update(metric_id, *, title=None, user_id=None, goal=None, min_goal=None, max_goal=None, units=None, rule=None, notes=None) -> Metric` | Update a metric. |
| `archive()` | `archive(metric_id) -> Metric` | Archive a metric. There is no `restore()`. |
| `scores()` | `scores(metric_id, start=None, end=None, include_empty=False) -> list[MetricScore]` | List a metric's scores, most recent first. |
| `set_score()` | `set_score(metric_id, value, timestamp) -> MetricScore` | Set a score for a given time. |
| `update_score()` | `update_score(metric_id, score_id, *, value=None, notes=None) -> MetricScore` | Update an existing score's value and/or note. |
| `clear_score()` | `clear_score(metric_id, score_id) -> MetricScore` | Clear a score's value, leaving an empty placeholder. |

## Description ("notes") behavior

Every entity with a `notes` field (`Issue`, `Headline`, `Todo`, `Goal`,
`Metric`) stores its description as a collaborative note pad (Etherpad), not
as a plain text column. This has one consequence you need to know:

!!! warning "`notes=` on `update()` creates a new pad, it does not edit the old one"
    Passing `notes=` to `create()` or `update()` always creates a **brand-new**
    note pad and points the entity at it (`notes_id`). It never edits the
    previous pad's content in place. Each `update(..., notes=...)` call
    replaces the entity's `notes_id` with a fresh pad, leaving the old pad
    orphaned. There is no way to append to or partially edit an existing note
    through this SDK — always pass the full new description text.

```python
issue = client.v2.issue.create(123, "Title", notes="Original text")
print(issue.notes_id)  # e.g. "abc123"

updated = client.v2.issue.update(issue.id, notes="Replacement text")
print(updated.notes_id)  # a different pad id
print(updated.notes)     # "Replacement text"
```

Reading `notes` immediately after a write can occasionally return stale or
empty text: pad reads are cached for a second or two after a write. If you
read a just-written note back and it looks empty, retry after a short delay
rather than assuming the write failed.

`notes_id` is kept on the model alongside `notes` for reference, but you do
not need it for normal use — pass a new `notes=` string to `update()` to
replace the description.

## Archive vs. delete semantics per entity

Lifecycle operations are not uniform across entities — some archive, some
complete/reopen, and milestones delete outright. There is no cross-entity
`delete()` for issues, headlines, todos, goals, or metrics; they only
archive/restore.

| Entity | Lifecycle methods | Notes |
|---|---|---|
| Issue | `solve()` / `reopen()`, `archive()` / `restore()` | The API stores long-term issues with an archived flag; the SDK reports them as not archived, matching the web app. `archive()` removes a long-term issue from the long-term list, and `restore()` returns it to the short-term list. Solve an issue before archiving it: `solve()` has no effect on an archived issue. |
| Headline | `archive()` / `restore()` | No complete/solve concept. |
| Todo | `complete()` / `reopen()`, `archive()` / `restore()` | Independent flags: a to-do can be completed and archived at the same time. |
| Goal | `archive()` / `restore()` | `archive()` re-reads the goal after the mutation and raises `GraphQLError` if it is still not archived, working around a server-side bug where the edit can report success without archiving anything. `restore()` re-attaches meeting links detached by a recent archive. |
| Milestone | `delete()` | No archive/restore — `delete()` permanently removes it (soft-deleted server-side; it never reappears). There is no root query to read a milestone directly, which is why `update()` and `complete()` require both `milestone_id` and `goal_id`. |
| Metric | `archive()` | **No `restore()`.** The GraphQL API does not support un-archiving a metric — editing `archived: false` on an already-archived metric re-archives it rather than restoring it. Archiving a metric is effectively permanent through this SDK. |

## Metric scores and week semantics

`client.v2.metric` scores have a few behaviors worth knowing before you write
data:

- **`set_score()` upserts by period for weekly/monthly/quarterly metrics.**
  Calling it twice for timestamps in the same period updates the same score
  row. For `MetricFrequency.DAILY` metrics, a placeholder score already
  exists for every day, so `set_score()` transparently falls back to
  `update_score()` when it detects that placeholder instead of creating a
  duplicate.
- **Weekly scores are stored on the Sunday-anchored start of their week**, not
  the exact instant you pass. Writing a score with `timestamp=datetime.now()`
  on a Thursday stores it on that week's preceding Sunday at `00:00 UTC` —
  reading `MetricScore.week_date` back will reflect that anchor, not "now".
- **`clear_score()` blanks a score's value** but keeps the row as an empty
  placeholder — it does not delete it. `scores(include_empty=True)` will
  still return it with `value=None`.
- **`rule=MetricRule.BETWEEN` requires `min_goal`/`max_goal` instead of
  `goal`.** Mixing the two raises `ValueError` locally, before any request is
  sent:

```python
from bloomy import Client
from bloomy.v2.models import MetricRule

with Client(api_key="your-api-key") as client:
    # OK: single goal for a non-BETWEEN rule
    client.v2.metric.create(123, "Response Time", goal=24, rule=MetricRule.LESS_THAN)

    # OK: min/max goal for BETWEEN
    client.v2.metric.create(
        123, "Team Size", min_goal=5, max_goal=10, rule=MetricRule.BETWEEN
    )

    # Raises ValueError: `goal` cannot be used with rule=BETWEEN
    client.v2.metric.create(123, "Bad Example", goal=5, rule=MetricRule.BETWEEN)
```

## GraphQLError

v2 operations raise `bloomy.GraphQLError` (a subclass of `APIError`, itself a
subclass of `BloomyError`) instead of a plain `APIError`, so existing
`except APIError` / `except BloomyError` handlers keep working without
changes. `GraphQLError` adds an `errors` attribute: the raw list of GraphQL
error objects from the response.

A `GraphQLError` is raised for:

- A response body carrying a top-level `errors` array, whether it came back
  with an HTTP 4xx validation status or an HTTP 200 execution status.
- A mutation result shaped `{success, message, errorDetails}` where `success`
  is `false` (used by, for example, `issue.update()` and
  `milestone.delete()`).

!!! note "Some v2 mutations return only `{id}`"
    A few mutations (`headline`/`goal`/`milestone`/`metric` create and edit)
    return only `IdModel { id }` rather than the
    `{success, message, errorDetails}` shape. For those, failures surface
    exclusively through the top-level `errors` array — there is no
    `success: false` body to check. This is transparent to callers: either
    way, a failed write raises `GraphQLError`.

```python
from bloomy import Client, GraphQLError

with Client(api_key="your-api-key") as client:
    try:
        client.v2.issue.update(123)  # no fields -> ValueError (local, not GraphQLError)
    except ValueError as e:
        print(f"Validation error: {e}")

    try:
        client.v2.issue.details(999999999)
    except GraphQLError as e:
        print(f"GraphQL error: {e}")
        print(f"Status code: {e.status_code}")
        print(f"Raw errors: {e.errors}")
```

## Next steps

- [v2 API Reference](../api/v2/user.md) — full method and model documentation
  for every `client.v2` namespace.
- [Basic Usage](usage.md) — v1 (REST) patterns.
- [Error Handling](errors.md) — the full `BloomyError` hierarchy.
