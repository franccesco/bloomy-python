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

=== "Sync"

    ```python
    from bloomy import Client
    
    with Client(api_key="your-api-key") as client:
        # List all meetings
        meetings = client.meeting.list()
        for meeting in meetings:
            print(f"{meeting.name} - {meeting.meeting_date}")
        
        # Get meeting details with all related data
        meeting = client.meeting.details(meeting_id=123)
        print(f"Attendees: {len(meeting.attendees)}")
        print(f"Open Issues: {len([i for i in meeting.issues if not i.closed])}")
        print(f"Todos: {len(meeting.todos)}")
        
        # Get metrics for a meeting
        metrics = client.meeting.metrics(meeting_id=123)
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient
    
    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # List all meetings
            meetings = await client.meeting.list()
            for meeting in meetings:
                print(f"{meeting.name} - {meeting.meeting_date}")
            
            # Get meeting details with all related data
            meeting = await client.meeting.details(meeting_id=123)
            print(f"Attendees: {len(meeting.attendees)}")
            print(f"Open Issues: {len([i for i in meeting.issues if not i.closed])}")
            print(f"Todos: {len(meeting.todos)}")
            
            # Get metrics for a meeting
            metrics = await client.meeting.metrics(meeting_id=123)
    
    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `list()` | Get all meetings | `include_closed` |
| `details()` | Get detailed meeting information with attendees, issues, todos, and metrics | `meeting_id` |
| `attendees()` | Get meeting attendees | `meeting_id` |
| `issues()` | Get issues from a meeting | `meeting_id` |
| `todos()` | Get todos from a meeting | `meeting_id` |
| `metrics()` | Get scorecard metrics from a meeting | `meeting_id` |