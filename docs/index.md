# Bloomy Python SDK

A Python SDK for interacting with the [Bloom Growth](https://www.bloomgrowth.com/) API.

## Features

- **Simple Authentication** - API key based authentication with multiple configuration options
- **Comprehensive Coverage** - Access to users, meetings, todos, goals, scorecards, issues, and headlines
- **Type Safety** - Full type annotations for better IDE support and code reliability
- **Pythonic API** - Intuitive, Python-friendly interface with proper error handling
- **Full Async Support** - Complete async/await support for all operations with dedicated AsyncClient for modern Python applications
- **Bulk Operations** - Efficient bulk creation for issues, todos, meetings, and goals with detailed error handling

## Quick Example

=== "Sync"

    ```python
    from bloomy import Client

    # Initialize the client
    client = Client(api_key="your-api-key")

    # Get current user
    user = client.user.details()
    print(f"Hello, {user.name}!")

    # List meetings
    meetings = client.meeting.list()
    for meeting in meetings:
        print(f"Meeting: {meeting.name}")

    # Create a todo
    meeting_id = meetings[0].id
    todo = client.todo.create(
        title="Review Q4 metrics",
        meeting_id=meeting_id,
        due_date="2024-12-31"
    )
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        # Initialize the async client
        async with AsyncClient(api_key="your-api-key") as client:
            # Get current user
            user = await client.user.details()
            print(f"Hello, {user.name}!")

            # List meetings
            meetings = await client.meeting.list()
            for meeting in meetings:
                print(f"Meeting: {meeting.name}")

            # Create a todo
            meeting_id = meetings[0].id
            todo = await client.todo.create(
                title="Review Q4 metrics",
                meeting_id=meeting_id,
                due_date="2024-12-31"
            )

    asyncio.run(main())
    ```

## Installation

```bash
pip install bloomy-python
```

Or with uv:

```bash
uv add bloomy-python
```

## Requirements

- Python 3.12+
- A Bloom Growth account with API access

## Next Steps

- [Installation Guide](getting-started/installation.md) - Detailed installation instructions
- [Quick Start](getting-started/quickstart.md) - Get up and running quickly
- [API Reference](api/client.md) - Complete API documentation
- [GitHub Repository](https://github.com/franccesco/bloomy-python) - Source code and issue tracking