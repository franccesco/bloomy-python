# Todo Operations

Operations for managing todos and todo-related data.

## API Reference

::: bloomy.operations.todos.TodoOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncTodoOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.todos.AsyncTodoOperations
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
        # List todos for current user
        todos = client.todo.list()
        for todo in todos:
            print(f"{todo.name} - Due: {todo.due_date}")
        
        # List todos for a specific meeting
        meeting_todos = client.todo.list(meeting_id=123)
        
        # Create a new todo
        new_todo = client.todo.create(
            title="Review quarterly report",
            meeting_id=123,
            due_date="2024-12-31"
        )
        
        # Update a todo
        client.todo.update(
            todo_id=new_todo.id,
            title="Review Q4 report",
            due_date="2024-12-15"
        )
        
        # Mark a todo as complete
        client.todo.complete(todo_id=new_todo.id)
        
        # Delete a todo
        client.todo.delete(todo_id=new_todo.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    
    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # List todos for current user
            todos = await client.todo.list()
            for todo in todos:
                print(f"{todo.name} - Due: {todo.due_date}")
            
            # List todos for a specific meeting
            meeting_todos = await client.todo.list(meeting_id=123)
            
            # Create a new todo
            new_todo = await client.todo.create(
                title="Review quarterly report",
                meeting_id=123,
                due_date="2024-12-31"
            )
            
            # Update a todo
            await client.todo.update(
                todo_id=new_todo.id,
                title="Review Q4 report",
                due_date="2024-12-15"
            )
            
            # Mark a todo as complete
            await client.todo.complete(todo_id=new_todo.id)
            
            # Delete a todo
            await client.todo.delete(todo_id=new_todo.id)
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `list()` | Get todos | `user_id`, `meeting_id`, `include_closed` |
| `details()` | Get detailed todo information | `todo_id` |
| `create()` | Create a new todo | `title`, `meeting_id`, `user_id`, `due_date` |
| `update()` | Update an existing todo | `todo_id`, `title`, `meeting_id`, `user_id`, `due_date` |
| `delete()` | Delete a todo | `todo_id` |
| `complete()` | Mark a todo as complete | `todo_id` |

!!! note "Filtering"
    You can filter todos by either `user_id` or `meeting_id`, but not both at the same time.