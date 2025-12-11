# Headline Operations

Operations for managing headlines and headline-related data.

## API Reference

::: bloomy.operations.headlines.HeadlineOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncHeadlineOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.headlines.AsyncHeadlineOperations
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
        headline = client.headline.create(
            meeting_id=123,
            title="Product launch successful",
            notes="Exceeded targets by 15%"
        )
        
        # Get headline details
        details = client.headline.details(headline_id=headline.id)
        print(f"Created: {details.created_at}")
        print(f"Archived: {details.archived}")
        
        # List headlines for current user
        headlines = client.headline.list()
        
        # List headlines for a specific meeting
        meeting_headlines = client.headline.list(meeting_id=123)
        
        # Update headline title (returns None)
        client.headline.update(
            headline_id=headline.id,
            title="Product launch exceeded expectations"
        )

        # Delete headline (returns None)
        client.headline.delete(headline_id=headline.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    
    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a new headline
            headline = await client.headline.create(
                meeting_id=123,
                title="Product launch successful",
                notes="Exceeded targets by 15%"
            )
            
            # Get headline details
            details = await client.headline.details(headline_id=headline.id)
            print(f"Created: {details.created_at}")
            print(f"Archived: {details.archived}")
            
            # List headlines for current user
            headlines = await client.headline.list()
            
            # List headlines for a specific meeting
            meeting_headlines = await client.headline.list(meeting_id=123)
            
            # Update headline title (returns None)
            await client.headline.update(
                headline_id=headline.id,
                title="Product launch exceeded expectations"
            )

            # Delete headline (returns None)
            await client.headline.delete(headline_id=headline.id)
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `create()` | Create a new headline | `meeting_id`, `title`, `owner_id`, `notes` |
| `update()` | Update a headline title | `headline_id`, `title` |
| `details()` | Get detailed headline information | `headline_id` |
| `list()` | Get headlines | `user_id`, `meeting_id` |
| `delete()` | Delete a headline | `headline_id` |

!!! note "Filtering"
    Like todos, headlines can be filtered by either `user_id` or `meeting_id`, but not both.

!!! note "Return Values"
    The `update()` and `delete()` methods return `None` instead of boolean values.