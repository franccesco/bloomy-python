# User Operations (v2)

GraphQL operations for reading users. See the [v2 guide](../../guide/v2-graphql-api.md)
for how `client.v2` relates to `client.v1`/`client.user`.

## API Reference

::: bloomy.v2.operations.user.UserOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncUserOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.user.AsyncUserOperations
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
        # Get current user details
        me = client.v2.user.details()
        print(f"Name: {me.full_name}")

        # Get a specific user
        user = client.v2.user.details(user_id=456)

        # List every user in the organization
        all_users = client.v2.user.list()
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Get current user details
            me = await client.v2.user.details()
            print(f"Name: {me.full_name}")

            # Get a specific user
            user = await client.v2.user.details(user_id=456)

            # List every user in the organization
            all_users = await client.v2.user.list()

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `details()` | Get a user | `user_id` (optional, defaults to current user) | `User` |
| `list()` | List every user in the organization, ordered by full name | None | `list[User]` |

!!! note "Scope"
    `client.v2.user` is read-only. There is no `client.v2` equivalent of
    `client.v1.user.search()`, `direct_reports()`, or `positions()` — use
    `client.user` (v1) for those.
