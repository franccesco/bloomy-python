# Meeting Operations (v2)

GraphQL operations for reading meetings and their attendees. See the
[v2 guide](../../guide/v2-graphql-api.md) for how `client.v2` relates to
`client.v1`/`client.meeting`.

## API Reference

::: bloomy.v2.operations.meeting.MeetingOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncMeetingOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.meeting.AsyncMeetingOperations
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
        # List meetings the current user attends
        meetings = client.v2.meeting.list()
        for meeting in meetings:
            print(f"{meeting.name} (ID: {meeting.id})")

        # List meetings for a specific user
        meetings = client.v2.meeting.list(user_id=456)

        # Get meeting details, including attendees
        meeting = client.v2.meeting.details(meetings[0].id)
        print(f"Attendees: {len(meeting.attendees)}")

        # List just the attendees
        attendees = client.v2.meeting.attendees(meeting.id)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # List meetings the current user attends
            meetings = await client.v2.meeting.list()
            for meeting in meetings:
                print(f"{meeting.name} (ID: {meeting.id})")

            # List meetings for a specific user
            meetings = await client.v2.meeting.list(user_id=456)

            # Get meeting details, including attendees
            meeting = await client.v2.meeting.details(meetings[0].id)
            print(f"Attendees: {len(meeting.attendees)}")

            # List just the attendees
            attendees = await client.v2.meeting.attendees(meeting.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list()` | List meetings a user attends, ordered by name | `user_id` (optional, defaults to current user) | `list[MeetingListItem]` |
| `details()` | Get a meeting, including its attendees | `meeting_id` | `Meeting` |
| `attendees()` | List a meeting's attendees, ordered by full name | `meeting_id` | `list[User]` |

!!! note "Scope"
    `client.v2.meeting` is read-only. There is no `client.v2` equivalent of
    `client.v1.meeting.create()`, `delete()`, `issues()`, `todos()`, or
    `metrics()` — use `client.meeting` (v1), or query `client.v2.issue`,
    `client.v2.todo`, and `client.v2.metric` directly with a `meeting_id`.
