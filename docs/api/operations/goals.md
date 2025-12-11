# Goal Operations

Operations for managing goals (also known as "rocks") and goal-related data.

## API Reference

::: bloomy.operations.goals.GoalOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncGoalOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.goals.AsyncGoalOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      members: false
      show_bases: false
      show_inheritance_diagram: false

!!! info "Async Usage"
    All methods have the same parameters and return types as their sync counterparts. Simply add `await` before each method call. The `create_many()` method has an additional `max_concurrent` parameter in the async version for controlling concurrency.

## Goal Status Enum

The SDK provides a `GoalStatus` enum for type-safe status updates:

```python
from bloomy import GoalStatus

# Enum values (recommended)
GoalStatus.ON_TRACK     # "on" - Goal is on track
GoalStatus.AT_RISK      # "off" - Goal is at risk
GoalStatus.COMPLETE     # "complete" - Goal is complete

# You can still use strings directly
client.goal.update(goal_id=123, status="on")
```

!!! tip "Using the Enum"
    Using `GoalStatus` enum values is recommended for better type checking and IDE autocomplete support.

## Usage Examples

=== "Sync"

    ```python
    from bloomy import Client, GoalStatus

    with Client(api_key="your-api-key") as client:
        # List active goals
        goals = client.goal.list()
        for goal in goals:
            print(f"{goal.title} - Status: {goal.status}")

        # List with archived goals included
        all_goals = client.goal.list(archived=True)
        print(f"Active: {len(all_goals.active)}")
        print(f"Archived: {len(all_goals.archived)}")

        # Create a new goal
        new_goal = client.goal.create(
            title="Increase customer retention by 20%",
            meeting_id=123
        )

        # Update goal status using enum (recommended)
        client.goal.update(
            goal_id=new_goal.id,
            status=GoalStatus.ON_TRACK
        )

        # Or use string directly
        client.goal.update(goal_id=new_goal.id, status="off")  # at risk

        # Archive and restore (both return None)
        client.goal.archive(goal_id=new_goal.id)
        client.goal.restore(goal_id=new_goal.id)

        # Delete a goal (returns None)
        client.goal.delete(goal_id=new_goal.id)

        # Bulk create multiple goals
        goals_data = [
            {"title": "Increase revenue by 20%", "meeting_id": 123},
            {"title": "Launch new product", "meeting_id": 123, "user_id": 456},
        ]
        result = client.goal.create_many(goals_data)

        print(f"Created {len(result.successful)} goals")
        for error in result.failed:
            print(f"Failed at index {error.index}: {error.error}")
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient, GoalStatus

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # List active goals
            goals = await client.goal.list()
            for goal in goals:
                print(f"{goal.title} - Status: {goal.status}")

            # List with archived goals included
            all_goals = await client.goal.list(archived=True)
            print(f"Active: {len(all_goals.active)}")
            print(f"Archived: {len(all_goals.archived)}")

            # Create a new goal
            new_goal = await client.goal.create(
                title="Increase customer retention by 20%",
                meeting_id=123
            )

            # Update goal status using enum (recommended)
            await client.goal.update(
                goal_id=new_goal.id,
                status=GoalStatus.ON_TRACK
            )

            # Or use string directly
            await client.goal.update(goal_id=new_goal.id, status="off")  # at risk

            # Archive and restore (both return None)
            await client.goal.archive(goal_id=new_goal.id)
            await client.goal.restore(goal_id=new_goal.id)

            # Delete a goal (returns None)
            await client.goal.delete(goal_id=new_goal.id)

            # Bulk create with concurrency control
            result = await client.goal.create_many(goals_data, max_concurrent=10)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `list()` | Get goals for a user | `user_id`, `archived` |
| `create()` | Create a new goal | `title`, `meeting_id`, `user_id` |
| `create_many()` | Create multiple goals in bulk | `goals` (sync); `goals`, `max_concurrent` (async) |
| `update()` | Update an existing goal | `goal_id`, `title`, `accountable_user`, `status` |
| `delete()` | Delete a goal | `goal_id` |
| `archive()` | Archive a goal | `goal_id` |
| `restore()` | Restore an archived goal | `goal_id` |

!!! info "Status Values"
    Valid status values are: `'on'` (On Track), `'off'` (At Risk), or `'complete'` (Completed). Use the `GoalStatus` enum for type-safe updates.

!!! note "Return Values"
    The `update()`, `delete()`, `archive()`, and `restore()` methods return `None` instead of boolean values.