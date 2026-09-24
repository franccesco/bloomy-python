# Issue Operations (v2)

GraphQL operations for managing issues. See the [v2 guide](../../guide/v2-graphql-api.md)
for how `client.v2` relates to `client.v1`/`client.issue`, and for the
description ("notes") and archive/restore behavior shared across v2 entities.

## API Reference

::: bloomy.v2.operations.issue.IssueOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncIssueOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.issue.AsyncIssueOperations
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
        issue = client.v2.issue.create(
            meeting_id=123,
            title="Server performance degradation",
            notes="Response times increased by 50% during peak hours",
        )

        # Get issue details
        details = client.v2.issue.details(issue.id)
        print(f"Owner: {details.owner.full_name if details.owner else 'Unassigned'}")

        # List short-term issues for a meeting
        meeting_issues = client.v2.issue.list(meeting_id=123)

        # Include recently solved and archived issues too
        all_issues = client.v2.issue.list(
            meeting_id=123, include_solved=True, include_archived=True
        )

        # List long-term (department plan) issues instead
        long_term_issues = client.v2.issue.list(meeting_id=123, long_term=True)

        # Update an issue
        updated = client.v2.issue.update(issue.id, title="Updated title")

        # Solve, then reopen
        solved = client.v2.issue.solve(issue.id)
        reopened = client.v2.issue.reopen(issue.id)

        # Archive, then restore
        client.v2.issue.archive(issue.id)
        client.v2.issue.restore(issue.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a new issue
            issue = await client.v2.issue.create(
                meeting_id=123,
                title="Server performance degradation",
                notes="Response times increased by 50% during peak hours",
            )

            # Get issue details
            details = await client.v2.issue.details(issue.id)

            # List short-term issues for a meeting
            meeting_issues = await client.v2.issue.list(meeting_id=123)

            # Update an issue
            updated = await client.v2.issue.update(issue.id, title="Updated title")

            # Solve, then reopen
            solved = await client.v2.issue.solve(issue.id)
            reopened = await client.v2.issue.reopen(issue.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `details()` | Get an issue | `issue_id` | `Issue` |
| `list()` | List issues for a meeting | `meeting_id`, `long_term`, `include_solved`, `include_archived` | `list[Issue]` |
| `create()` | Create an issue | `meeting_id`, `title`, `user_id`, `notes`, `long_term` | `Issue` |
| `update()` | Update an issue | `issue_id`, `title`, `user_id`, `notes`, `long_term`, `meeting_id` | `Issue` |
| `solve()` | Mark an issue as solved | `issue_id` | `Issue` |
| `reopen()` | Reopen a solved issue | `issue_id` | `Issue` |
| `archive()` | Archive an issue | `issue_id` | `Issue` |
| `restore()` | Restore an archived (short-term) issue | `issue_id` | `Issue` |

!!! note "Long-term issues"
    Setting `long_term=True` on `create()` or `update()` moves an issue to the
    long-term (department plan) list, and `list(long_term=True)` returns that
    list. `include_solved` and `include_archived` have no effect in that mode.
    The API stores long-term issues with an archived flag, but the SDK reports
    `archived=False` for them because the web app shows them on the Long-Term
    tab. `archive()` removes a long-term issue from that list, and `restore()`
    brings it back to the short-term list. Use
    `update(issue_id, long_term=False)` to move an issue back to short term
    without archiving it.

!!! note "Update requirements"
    At least one field must be provided to `update()`, or it raises `ValueError`.
