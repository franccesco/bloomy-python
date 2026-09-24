# To-do Operations (v2)

GraphQL operations for managing to-dos. See the [v2 guide](../../guide/v2-graphql-api.md)
for how `client.v2` relates to `client.v1`/`client.todo`, and for the
description ("notes") behavior shared across v2 entities.

## API Reference

::: bloomy.v2.operations.todo.TodoOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncTodoOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.todo.AsyncTodoOperations
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
        # Create a to-do in a meeting (due date defaults to 7 days from today)
        todo = client.v2.todo.create(
            title="Review Q4 metrics",
            meeting_id=123,
            notes="Cross-check against last quarter",
        )

        # Create a personal to-do (no meeting_id)
        personal_todo = client.v2.todo.create(title="Renew certification")

        # Get to-do details
        details = client.v2.todo.details(todo.id)

        # List open to-dos for a meeting
        meeting_todos = client.v2.todo.list(meeting_id=123)

        # Include completed and archived to-dos too
        all_todos = client.v2.todo.list(
            meeting_id=123, include_completed=True, include_archived=True
        )

        # Update title and due date
        updated = client.v2.todo.update(todo.id, title="New title", due_date="2026-01-15")

        # Complete, then reopen
        client.v2.todo.complete(todo.id)
        client.v2.todo.reopen(todo.id)

        # Archive, then restore
        client.v2.todo.archive(todo.id)
        client.v2.todo.restore(todo.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a to-do in a meeting (due date defaults to 7 days from today)
            todo = await client.v2.todo.create(
                title="Review Q4 metrics",
                meeting_id=123,
                notes="Cross-check against last quarter",
            )

            # List open to-dos for a meeting
            meeting_todos = await client.v2.todo.list(meeting_id=123)

            # Complete, then reopen
            await client.v2.todo.complete(todo.id)
            await client.v2.todo.reopen(todo.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `details()` | Get a to-do | `todo_id` | `Todo` |
| `list()` | List to-dos for a meeting or a user | `meeting_id`, `user_id`, `include_completed`, `include_archived` | `list[Todo]` |
| `create()` | Create a to-do | `title`, `meeting_id`, `user_id`, `due_date`, `notes` | `Todo` |
| `update()` | Update a to-do | `todo_id`, `title`, `due_date`, `user_id`, `notes` | `Todo` |
| `complete()` | Mark a to-do as complete | `todo_id` | `Todo` |
| `reopen()` | Reopen a completed to-do | `todo_id` | `Todo` |
| `archive()` | Archive a to-do | `todo_id` | `Todo` |
| `restore()` | Restore an archived to-do | `todo_id` | `Todo` |

!!! note "Filtering"
    `list()` accepts either `meeting_id` or `user_id`, not both. Passing both
    raises `ValueError`. If neither is given, it defaults to the current user.
    `include_archived` has no effect when listing by `user_id`: the
    underlying query excludes archived to-dos unconditionally, server-side.
    Omit `meeting_id` on `create()` for a personal to-do — it is always
    assigned to the caller regardless of `user_id`.

!!! note "Update requirements"
    At least one field must be provided to `update()`, or it raises
    `ValueError`. A due date can be changed but not cleared.
