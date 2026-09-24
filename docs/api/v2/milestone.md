# Milestone Operations (v2)

GraphQL operations for managing a goal's milestones. There is no v1
equivalent — milestones are new in the v2 API. See the
[v2 guide](../../guide/v2-graphql-api.md) for archive/delete semantics across
v2 entities, and [Goal Operations](goal.md) for creating milestones alongside
a goal.

## API Reference

::: bloomy.v2.operations.milestone.MilestoneOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncMilestoneOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.milestone.AsyncMilestoneOperations
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

    with Client(api_key="your-api-key") as client:
        # Create a milestone on an existing goal
        milestone = client.v2.milestone.create(
            goal_id=5265048,
            title="Draft spec",
            due_date=date(2026, 1, 1),
        )

        # List a goal's milestones
        milestones = client.v2.milestone.list(goal_id=5265048)

        # Update it (goal_id is keyword-only: verified before anything is
        # written, and needed again to re-read the milestone afterward)
        updated = client.v2.milestone.update(
            milestone.id, goal_id=milestone.goal_id, title="Draft spec v2"
        )

        # Mark it complete
        completed = client.v2.milestone.complete(
            milestone.id, goal_id=milestone.goal_id
        )

        # Delete it (no goal_id needed, and there is no restore)
        client.v2.milestone.delete(milestone.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    from datetime import date

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a milestone on an existing goal
            milestone = await client.v2.milestone.create(
                goal_id=5265048,
                title="Draft spec",
                due_date=date(2026, 1, 1),
            )

            # Mark it complete
            completed = await client.v2.milestone.complete(
                milestone.id, goal_id=milestone.goal_id
            )

            # Delete it
            await client.v2.milestone.delete(milestone.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list()` | List a goal's milestones, ordered by due date | `goal_id` | `list[Milestone]` |
| `create()` | Create a milestone on a goal | `goal_id`, `title`, `due_date`, `completed` | `Milestone` |
| `update()` | Update a milestone | `milestone_id`, `goal_id` (keyword-only), `title`, `due_date`, `completed` | `Milestone` |
| `complete()` | Mark a milestone as completed | `milestone_id`, `goal_id` (keyword-only) | `Milestone` |
| `delete()` | Delete a milestone | `milestone_id` | `None` |

!!! note "Why `update()` and `complete()` need `goal_id`"
    There is no root GraphQL query to read a single milestone by id — a
    milestone can only be read through its parent goal
    (`goal(id){ milestones }`). `update()` and `complete()` need `goal_id`
    (keyword-only) in addition to `milestone_id`: both verify that
    `milestone_id` actually belongs to `goal_id` **before** sending any edit,
    so a wrong `goal_id` fails without writing anything, and then need
    `goal_id` again to re-read the milestone afterward. `delete()` needs
    neither, since `DeleteMilestone` does not return a `Milestone`.

!!! note "No archive/restore — only delete"
    Milestones do not archive; `delete()` permanently removes one
    (soft-deleted server-side, but with no SDK-exposed way to bring it back).

!!! note "Update requirements"
    At least one field must be provided to `update()`, or it raises `ValueError`.
