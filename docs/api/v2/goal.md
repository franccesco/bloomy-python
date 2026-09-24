# Goal Operations (v2)

GraphQL operations for managing goals (rocks). See the [v2 guide](../../guide/v2-graphql-api.md)
for how `client.v2` relates to `client.v1`/`client.goal`, and for the
description ("notes") behavior shared across v2 entities. For working with a
goal's milestones individually, see [Milestone Operations](milestone.md).

## API Reference

::: bloomy.v2.operations.goal.GoalOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncGoalOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.goal.AsyncGoalOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      members: false
      show_bases: false
      show_inheritance_diagram: false

!!! info "Async Usage"
    All methods have the same parameters and return types as their sync counterparts. Simply add `await` before each method call.

## Usage Examples

=== "Sync"

    ```python
    from datetime import date
    from bloomy import Client
    from bloomy.v2.models import GoalStatus

    with Client(api_key="your-api-key") as client:
        # Create a goal (due date defaults to 90 days from today)
        goal = client.v2.goal.create(
            meeting_id=123,
            title="Ship v2",
            notes="Launch details",
        )

        # Create a goal with milestones in the same call
        goal_with_milestones = client.v2.goal.create(
            meeting_id=123,
            title="Ship v2",
            milestones=[
                {"title": "Draft spec", "due_date": date(2026, 1, 1)},
                ("Beta release", date(2026, 2, 1)),
            ],
        )

        # Get goal details, including milestones
        details = client.v2.goal.details(goal.id)
        for milestone in details.milestones:
            print(f"{milestone.title}: completed={milestone.completed}")

        # List goals for a meeting
        meeting_goals = client.v2.goal.list(meeting_id=123)

        # List goals for the current user, including archived ones
        my_goals = client.v2.goal.list(include_archived=True)

        # Update status using the v2 enum (ON_TRACK / OFF_TRACK / COMPLETED)
        updated = client.v2.goal.update(goal.id, status=GoalStatus.OFF_TRACK)

        # Archive, then restore
        client.v2.goal.archive(goal.id)
        client.v2.goal.restore(goal.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    from bloomy.v2.models import GoalStatus

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a goal (due date defaults to 90 days from today)
            goal = await client.v2.goal.create(
                meeting_id=123,
                title="Ship v2",
                notes="Launch details",
            )

            # Get goal details, including milestones
            details = await client.v2.goal.details(goal.id)

            # Update status using the v2 enum (ON_TRACK / OFF_TRACK / COMPLETED)
            updated = await client.v2.goal.update(goal.id, status=GoalStatus.OFF_TRACK)

            # Archive, then restore
            await client.v2.goal.archive(goal.id)
            await client.v2.goal.restore(goal.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list()` | List goals for a meeting or a user | `meeting_id`, `user_id`, `include_archived` | `list[Goal]` |
| `details()` | Get a goal, including its milestones | `goal_id` | `Goal` |
| `create()` | Create a goal, optionally with milestones | `meeting_id`, `title`, `user_id`, `due_date`, `status`, `notes`, `milestones` | `Goal` |
| `update()` | Update a goal | `goal_id`, `title`, `status`, `due_date`, `user_id`, `notes` | `Goal` |
| `archive()` | Archive a goal | `goal_id` | `Goal` |
| `restore()` | Restore an archived goal | `goal_id` | `Goal` |

!!! note "`GoalStatus` is different from the v1 enum"
    `bloomy.v2.models.GoalStatus` (`ON_TRACK` / `OFF_TRACK` / `COMPLETED`) is a
    distinct enum from `bloomy.GoalStatus` (v1's `on` / `off` / `complete`).
    Import the v2 one from `bloomy.v2.models` when working with `client.v2.goal`.

!!! note "`milestones=` on `create()`"
    Each item is either `{"title": ..., "due_date": ..., "completed": ...}`
    (`completed` optional, defaults to `False`) or a `(title, due_date)` /
    `(title, due_date, completed)` tuple. To add milestones to an existing
    goal afterwards, use [`client.v2.milestone.create()`](milestone.md) instead.

!!! warning "`archive()` can raise `GraphQLError`"
    The underlying `EditGoal(archived: true)` mutation can report success
    without archiving anything, due to a server-side bug. `archive()` re-reads
    the goal after the edit and raises `GraphQLError` if it is still not
    archived, so a caught exception here reliably means the archive did not
    take effect — it is safe to retry.

!!! note "Update requirements"
    At least one field must be provided to `update()`, or it raises `ValueError`.
