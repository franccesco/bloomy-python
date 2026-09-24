# Headline Operations (v2)

GraphQL operations for managing headlines. See the [v2 guide](../../guide/v2-graphql-api.md)
for how `client.v2` relates to `client.v1`/`client.headline`, and for the
description ("notes") behavior shared across v2 entities.

## API Reference

::: bloomy.v2.operations.headline.HeadlineOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncHeadlineOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.headline.AsyncHeadlineOperations
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
        # Create a new headline
        headline = client.v2.headline.create(
            meeting_id=123,
            title="Product launch successful",
            notes="Exceeded targets by 15%",
        )

        # Get headline details
        details = client.v2.headline.details(headline.id)

        # List headlines for a meeting (open only, by default)
        meeting_headlines = client.v2.headline.list(meeting_id=123)

        # Include archived headlines too
        all_headlines = client.v2.headline.list(meeting_id=123, include_archived=True)

        # List headlines for the current user instead
        my_headlines = client.v2.headline.list()

        # Update the title
        updated = client.v2.headline.update(headline.id, title="Updated title")

        # Archive, then restore
        client.v2.headline.archive(headline.id)
        client.v2.headline.restore(headline.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a new headline
            headline = await client.v2.headline.create(
                meeting_id=123,
                title="Product launch successful",
                notes="Exceeded targets by 15%",
            )

            # List headlines for a meeting (open only, by default)
            meeting_headlines = await client.v2.headline.list(meeting_id=123)

            # Update the title
            updated = await client.v2.headline.update(headline.id, title="Updated title")

            # Archive, then restore
            await client.v2.headline.archive(headline.id)
            await client.v2.headline.restore(headline.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `details()` | Get a headline | `headline_id` | `Headline` |
| `list()` | List headlines for a meeting or a user | `meeting_id`, `user_id`, `include_archived` | `list[Headline]` |
| `create()` | Create a headline | `meeting_id`, `title`, `user_id`, `notes` | `Headline` |
| `update()` | Update a headline | `headline_id`, `title`, `user_id`, `notes` | `Headline` |
| `archive()` | Archive a headline | `headline_id` | `Headline` |
| `restore()` | Restore an archived headline | `headline_id` | `Headline` |

!!! note "Filtering"
    `list()` accepts either `meeting_id` or `user_id`, not both. Passing both
    raises `ValueError`. If neither is given, it defaults to the current user.

!!! note "Update requirements"
    At least one field must be provided to `update()`, or it raises `ValueError`.
