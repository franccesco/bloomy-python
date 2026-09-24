# v2 Models

Pydantic models returned by `client.v2` operations. See the
[v2 guide](../../guide/v2-graphql-api.md) for how these fit into the wider
SDK.

## Conventions

These conventions apply uniformly across every v2 model:

- **Aliases are camelCase**, matching the GraphQL field names verbatim (e.g.
  `Field(alias="dateCreated")`) — unlike v1's PascalCase REST aliases.
- **Owners are nested refs**: an entity's assignee is exposed as
  `owner: UserRef | None` (aliased from the GraphQL `assignee` field), never
  flattened into `owner_id`/`owner_name`. `owner` is `None` when unowned.
- **Related entities are nested refs** too: an issue's parent meeting is
  `meeting: MeetingRef | None`, not flattened into `meeting_id`/`meeting_name`.
- **Datetimes use the `_date` suffix** (`created_date`, `due_date`,
  `completed_date`, `archived_date`) and are always timezone-aware UTC
  `datetime` objects, converted from the API's unix-seconds floats.
- **Notes**: description text is exposed as `notes: str | None`, computed from
  the underlying note pad. `notes_id` is kept alongside it — see
  [Description ("notes") behavior](../../guide/v2-graphql-api.md#description-notes-behavior)
  in the v2 guide.

## Reference types

::: bloomy.v2.models.UserRef
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.MeetingRef
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Users

::: bloomy.v2.models.User
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Meetings

::: bloomy.v2.models.MeetingListItem
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.Meeting
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Issues

::: bloomy.v2.models.Issue
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Headlines

::: bloomy.v2.models.Headline
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## To-dos

::: bloomy.v2.models.Todo
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Goals and milestones

::: bloomy.v2.models.GoalStatus
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.Milestone
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.Goal
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Metrics

::: bloomy.v2.models.MetricUnit
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.MetricRule
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.MetricFrequency
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.Metric
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: bloomy.v2.models.MetricScore
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
