# Meeting Operations

Operations for managing meetings and meeting-related data.

## API Reference

::: bloomy.operations.meetings.MeetingOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncMeetingOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.meetings.AsyncMeetingOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      members: false
      show_bases: false
      show_inheritance_diagram: false

!!! tip "Performance Benefit"
    The async `details()` method fetches attendees, issues, todos, and metrics concurrently, providing better performance than the sync version which fetches them sequentially.

## Usage Examples

### Basic Operations

=== "Sync"

    ```python
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # List all meetings for a user
        meetings = client.meeting.list()
        for meeting in meetings:
            print(f"{meeting.name} (ID: {meeting.id})")

        # List meetings for a specific user
        meetings = client.meeting.list(user_id=456)

        # Get meeting details with all related data
        meeting = client.meeting.details(meeting_id=123)
        print(f"Attendees: {len(meeting.attendees)}")
        print(f"Open Issues: {len([i for i in meeting.issues if i.closed_date is None])}")
        print(f"Todos: {len(meeting.todos)}")

        # Get meeting details including closed items
        meeting = client.meeting.details(meeting_id=123, include_closed=True)

        # Get metrics for a meeting
        metrics = client.meeting.metrics(meeting_id=123)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # List all meetings for a user
            meetings = await client.meeting.list()
            for meeting in meetings:
                print(f"{meeting.name} (ID: {meeting.id})")

            # List meetings for a specific user
            meetings = await client.meeting.list(user_id=456)

            # Get meeting details with all related data
            meeting = await client.meeting.details(meeting_id=123)
            print(f"Attendees: {len(meeting.attendees)}")
            print(f"Open Issues: {len([i for i in meeting.issues if i.closed_date is None])}")
            print(f"Todos: {len(meeting.todos)}")

            # Get meeting details including closed items
            meeting = await client.meeting.details(meeting_id=123, include_closed=True)

            # Get metrics for a meeting
            metrics = await client.meeting.metrics(meeting_id=123)

    asyncio.run(main())
    ```

### Creating and Deleting Meetings

=== "Sync"

    ```python
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # Create a new meeting
        result = client.meeting.create(
            title="Weekly Team Meeting",
            add_self=True,
            attendees=[2, 3, 4]
        )
        print(f"Created meeting ID: {result['meeting_id']}")

        # Create a meeting without adding yourself
        result = client.meeting.create(
            title="Leadership Meeting",
            add_self=False,
            attendees=[5, 6]
        )

        # Delete a meeting
        success = client.meeting.delete(meeting_id=123)
        if success:
            print("Meeting deleted successfully")
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a new meeting
            result = await client.meeting.create(
                title="Weekly Team Meeting",
                add_self=True,
                attendees=[2, 3, 4]
            )
            print(f"Created meeting ID: {result['meeting_id']}")

            # Create a meeting without adding yourself
            result = await client.meeting.create(
                title="Leadership Meeting",
                add_self=False,
                attendees=[5, 6]
            )

            # Delete a meeting
            success = await client.meeting.delete(meeting_id=123)
            if success:
                print("Meeting deleted successfully")

    asyncio.run(main())
    ```

### Bulk Operations

=== "Sync"

    ```python
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # Batch retrieve multiple meetings
        result = client.meeting.get_many([123, 456, 789])
        for meeting in result.successful:
            print(f"{meeting.name}: {len(meeting.attendees)} attendees")
        for error in result.failed:
            print(f"Failed to retrieve meeting at index {error.index}: {error.error}")

        # Bulk create meetings
        meetings_to_create = [
            {"title": "Q1 Planning", "attendees": [2, 3]},
            {"title": "Team Standup", "add_self": True},
            {"title": "1:1 with Manager", "attendees": [5]}
        ]
        result = client.meeting.create_many(meetings_to_create)
        print(f"Created {len(result.successful)} meetings")
        for meeting in result.successful:
            print(f"Meeting ID {meeting['meeting_id']}: {meeting['title']}")
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Batch retrieve multiple meetings (with concurrency control)
            result = await client.meeting.get_many([123, 456, 789], max_concurrent=10)
            for meeting in result.successful:
                print(f"{meeting.name}: {len(meeting.attendees)} attendees")
            for error in result.failed:
                print(f"Failed to retrieve meeting at index {error.index}: {error.error}")

            # Bulk create meetings (with concurrency control)
            meetings_to_create = [
                {"title": "Q1 Planning", "attendees": [2, 3]},
                {"title": "Team Standup", "add_self": True},
                {"title": "1:1 with Manager", "attendees": [5]}
            ]
            result = await client.meeting.create_many(
                meetings_to_create,
                max_concurrent=3
            )
            print(f"Created {len(result.successful)} meetings")
            for meeting in result.successful:
                print(f"Meeting ID {meeting['meeting_id']}: {meeting['title']}")

    asyncio.run(main())
    ```

!!! note "Async Concurrency Control"
    The async versions of `get_many()` and `create_many()` support a `max_concurrent` parameter to control the number of simultaneous requests. This helps prevent rate limiting and manage server load. The default is 5 concurrent requests.

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `list()` | Get all meetings for a user | `user_id` (optional) | `list[MeetingListItem]` |
| `details()` | Get detailed meeting information with attendees, issues, todos, and metrics | `meeting_id`, `include_closed` (optional, default: False) | `MeetingDetails` |
| `attendees()` | Get meeting attendees | `meeting_id` | `list[MeetingAttendee]` |
| `issues()` | Get issues from a meeting | `meeting_id`, `include_closed` (optional, default: False) | `list[Issue]` |
| `todos()` | Get todos from a meeting | `meeting_id`, `include_closed` (optional, default: False) | `list[Todo]` |
| `metrics()` | Get scorecard metrics from a meeting | `meeting_id` | `list[ScorecardMetric]` |
| `create()` | Create a new meeting | `title`, `add_self` (optional, default: True), `attendees` (optional) | `dict` |
| `delete()` | Delete a meeting | `meeting_id` | `bool` |
| `create_many()` | Bulk create multiple meetings | `meetings` (list of dicts), `max_concurrent` (async only, default: 5) | `BulkCreateResult[dict]` |
| `get_many()` | Batch retrieve multiple meetings by ID | `meeting_ids`, `max_concurrent` (async only, default: 5) | `BulkCreateResult[MeetingDetails]` |