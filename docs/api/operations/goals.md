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
    All methods have the same parameters and return types as their sync counterparts. Simply add `await` before each method call.

## Usage Examples

=== "Sync"

    ```python
    from bloomy import Client
    
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
        
        # Update goal status
        client.goal.update(
            goal_id=new_goal.id,
            status="on"  # on track
        )
        
        # Archive and restore
        client.goal.archive(goal_id=new_goal.id)
        client.goal.restore(goal_id=new_goal.id)
        
        # Delete a goal
        client.goal.delete(goal_id=new_goal.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    
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
            
            # Update goal status
            await client.goal.update(
                goal_id=new_goal.id,
                status="on"  # on track
            )
            
            # Archive and restore
            await client.goal.archive(goal_id=new_goal.id)
            await client.goal.restore(goal_id=new_goal.id)
            
            # Delete a goal
            await client.goal.delete(goal_id=new_goal.id)
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `list()` | Get goals for a user | `user_id`, `archived` |
| `create()` | Create a new goal | `title`, `meeting_id`, `user_id` |
| `update()` | Update an existing goal | `goal_id`, `title`, `accountable_user`, `status` |
| `delete()` | Delete a goal | `goal_id` |
| `archive()` | Archive a goal | `goal_id` |
| `restore()` | Restore an archived goal | `goal_id` |

!!! info "Status Values"
    Valid status values are: `'on'` (On Track), `'off'` (At Risk), or `'complete'` (Completed)