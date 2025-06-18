# User Operations

Operations for managing users and user-related data.

## API Reference

::: bloomy.operations.users.UserOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncUserOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.users.AsyncUserOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      members: false
      show_bases: false
      show_inheritance_diagram: false

!!! info "Async Usage"
    All methods in `AsyncUserOperations` have the same parameters and return types as their sync counterparts. Simply add `await` before each method call and use within an async context.

## Usage Examples

=== "Sync"

    ```python
    from bloomy import Client
    
    with Client(api_key="your-api-key") as client:
        # Get current user details
        user = client.user.details()
        print(f"Name: {user.name}")
        
        # Search for users
        results = client.user.search("john")
        for user in results:
            print(f"Found: {user.name}")
        
        # Get all users
        all_users = client.user.all()
        
        # Get user with direct reports and positions
        user_full = client.user.details(
            user_id=123, 
            include_direct_reports=True,
            include_positions=True
        )
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    
    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Get current user details
            user = await client.user.details()
            print(f"Name: {user.name}")
            
            # Search for users
            results = await client.user.search("john")
            for user in results:
                print(f"Found: {user.name}")
            
            # Get all users
            all_users = await client.user.all()
            
            # Get user with direct reports and positions
            user_full = await client.user.details(
                user_id=123, 
                include_direct_reports=True,
                include_positions=True
            )
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `details()` | Get detailed information about a user | `user_id`, `include_direct_reports`, `include_positions`, `all` |
| `search()` | Search for users by name or email | `term` |
| `all()` | Get all users in the system | `include_placeholders` |
| `direct_reports()` | Get direct reports for a user | `user_id` |
| `positions()` | Get positions held by a user | `user_id` |