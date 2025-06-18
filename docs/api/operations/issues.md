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
        
        # Solve an issue (mark as completed)
        client.issue.solve(issue_id=issue.id)
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
            
            # Solve an issue (mark as completed)
            await client.issue.solve(issue_id=issue.id)
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `details()` | Get detailed issue information | `issue_id` |
| `list()` | Get issues | `user_id`, `meeting_id` |
| `create()` | Create a new issue | `meeting_id`, `title`, `user_id`, `notes` |
| `solve()` | Mark an issue as solved | `issue_id` |

!!! tip "Issue Resolution"
    Issues can only be marked as solved, not deleted. Use the `solve()` method to close an issue.