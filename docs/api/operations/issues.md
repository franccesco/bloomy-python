# Issue Operations

Operations for managing issues and issue-related data.

## API Reference

::: bloomy.operations.issues.IssueOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncIssueOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.issues.AsyncIssueOperations
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
        # Create a new issue
        issue = client.issue.create(
            meeting_id=123,
            title="Server performance degradation",
            notes="Response times increased by 50% during peak hours"
        )
        
        # Get issue details
        details = client.issue.details(issue_id=issue.id)
        print(f"Created: {details.created_at}")
        print(f"Meeting: {details.meeting_title}")
        print(f"Assigned to: {details.user_name}")
        
        # List issues for current user
        my_issues = client.issue.list()
        
        # List issues for a specific meeting
        meeting_issues = client.issue.list(meeting_id=123)

        # Update an issue
        updated = client.issue.update(
            issue_id=issue.id,
            title="Updated: Server performance degradation",
            notes="Added monitoring and identified bottleneck"
        )

        # Complete an issue (mark as solved)
        completed = client.issue.complete(issue_id=issue.id)
        print(f"Completed: {completed.title}")
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    
    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a new issue
            issue = await client.issue.create(
                meeting_id=123,
                title="Server performance degradation",
                notes="Response times increased by 50% during peak hours"
            )
            
            # Get issue details
            details = await client.issue.details(issue_id=issue.id)
            print(f"Created: {details.created_at}")
            print(f"Meeting: {details.meeting_title}")
            print(f"Assigned to: {details.user_name}")
            
            # List issues for current user
            my_issues = await client.issue.list()
            
            # List issues for a specific meeting
            meeting_issues = await client.issue.list(meeting_id=123)

            # Update an issue
            updated = await client.issue.update(
                issue_id=issue.id,
                title="Updated: Server performance degradation",
                notes="Added monitoring and identified bottleneck"
            )

            # Complete an issue (mark as solved)
            completed = await client.issue.complete(issue_id=issue.id)
            print(f"Completed: {completed.title}")
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `details()` | Get detailed issue information | `issue_id` | `IssueDetails` |
| `list()` | Get issues | `user_id`, `meeting_id` | `list[IssueListItem]` |
| `create()` | Create a new issue | `meeting_id`, `title`, `user_id`, `notes` | `CreatedIssue` |
| `create_many()` | Create multiple issues | `issues` | `BulkCreateResult[CreatedIssue]` |
| `update()` | Update an existing issue | `issue_id`, `title`, `notes` | `IssueDetails` |
| `complete()` | Mark an issue as solved | `issue_id` | `IssueDetails` |

!!! tip "Issue Management"
    - Issues can only be marked as solved, not deleted. Use the `complete()` method to close an issue.
    - The `complete()` method returns the updated issue details, allowing you to verify the completion.
    - Use `update()` to modify issue title or notes before completing.

## Update Examples

=== "Sync"

    ```python
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # Update issue title only
        updated = client.issue.update(123, title="New Title")

        # Update issue notes only
        updated = client.issue.update(123, notes="Additional context and details")

        # Update both title and notes
        updated = client.issue.update(
            issue_id=123,
            title="Critical: Database Connection Pool Exhausted",
            notes="Increased max connections from 100 to 200"
        )
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Update issue title only
            updated = await client.issue.update(123, title="New Title")

            # Update issue notes only
            updated = await client.issue.update(123, notes="Additional context and details")

            # Update both title and notes
            updated = await client.issue.update(
                issue_id=123,
                title="Critical: Database Connection Pool Exhausted",
                notes="Increased max connections from 100 to 200"
            )

    asyncio.run(main())
    ```

!!! note "Update Requirements"
    At least one of `title` or `notes` must be provided when calling `update()`. If neither is provided, a `ValueError` will be raised.

## Bulk Operations

### Creating Multiple Issues

=== "Sync"

    ```python
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # Create multiple issues at once
        issues = [
            {
                "meeting_id": 123,
                "title": "Server performance degradation",
                "notes": "Response times increased by 50%"
            },
            {
                "meeting_id": 123,
                "title": "Database connection pool exhausted",
                "user_id": 456,
                "notes": "Max connections reached during peak hours"
            },
            {
                "meeting_id": 789,
                "title": "Authentication service timeout"
            }
        ]

        result = client.issue.create_many(issues)

        # Check results
        print(f"Successfully created {len(result.successful)} issues")
        for issue in result.successful:
            print(f"- Issue #{issue.id}: {issue.title}")

        # Handle failures
        if result.failed:
            print(f"Failed to create {len(result.failed)} issues")
            for error in result.failed:
                print(f"- Index {error.index}: {error.error}")
                print(f"  Input: {error.input_data}")
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create multiple issues concurrently
            issues = [
                {
                    "meeting_id": 123,
                    "title": "Server performance degradation",
                    "notes": "Response times increased by 50%"
                },
                {
                    "meeting_id": 123,
                    "title": "Database connection pool exhausted",
                    "user_id": 456,
                    "notes": "Max connections reached during peak hours"
                },
                {
                    "meeting_id": 789,
                    "title": "Authentication service timeout"
                }
            ]

            # Control concurrency with max_concurrent parameter
            result = await client.issue.create_many(issues, max_concurrent=5)

            # Check results
            print(f"Successfully created {len(result.successful)} issues")
            for issue in result.successful:
                print(f"- Issue #{issue.id}: {issue.title}")

            # Handle failures
            if result.failed:
                print(f"Failed to create {len(result.failed)} issues")
                for error in result.failed:
                    print(f"- Index {error.index}: {error.error}")
                    print(f"  Input: {error.input_data}")

    asyncio.run(main())
    ```

!!! info "Async Rate Limiting"
    The async version of `create_many()` supports a `max_concurrent` parameter (default: 5) to control the maximum number of concurrent requests. This helps prevent rate limiting issues when creating large batches of issues.

    ```python
    # Process more items concurrently for better performance
    result = await client.issue.create_many(issues, max_concurrent=10)

    # Process items more slowly to avoid rate limits
    result = await client.issue.create_many(issues, max_concurrent=2)
    ```

!!! tip "Bulk Operation Best Practices"
    - **Best-effort approach**: `create_many()` continues processing even if some issues fail to create
    - **Check both lists**: Always inspect both `result.successful` and `result.failed` to handle partial failures
    - **Required fields**: Each issue dict must include `meeting_id` and `title`
    - **Optional fields**: `user_id` defaults to the authenticated user if not provided
    - **Error handling**: Failed creations include the original input data and error message for debugging