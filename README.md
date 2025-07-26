# Bloomy - Python SDK for Bloom Growth API

![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
[![Deploy Documentation](https://github.com/franccesco/bloomy-python/actions/workflows/docs.yml/badge.svg)](https://github.com/franccesco/bloomy-python/actions/workflows/docs.yml)

A Python SDK for interacting with the Bloom Growth API, providing easy access to users, meetings, todos, goals, scorecards, issues, and headlines.

✨ **New in v0.13.0**: Full async/await support with `AsyncClient` for better performance in async applications!

## Installation

```bash
pip install bloomy-python
```

## Quick Start

### Synchronous Client

```python
from bloomy import Client

# Initialize the client with your API key
client = Client(api_key="your-api-key-here")

# Or use environment variable BG_API_KEY
client = Client()

# Or configure API key with username and password
from bloomy import Configuration

config = Configuration()
config.configure_api_key("username", "password", store_key=True)
client = Client()
```

### Asynchronous Client

```python
import asyncio
from bloomy import AsyncClient

async def main():
    # Use async client for better performance
    async with AsyncClient(api_key="your-api-key-here") as client:
        user = await client.user.details()
        meetings = await client.meeting.list()
        print(f"Hello {user.name}, you have {len(meetings)} meetings")

asyncio.run(main())
```

## Features

### Users

```python
# Get current user details
user = client.user.details()

# Get user with direct reports and positions
user = client.user.details(user_id=123, all=True)

# Search users
results = client.user.search("john")

# Get all users
users = client.user.all()
```

### Meetings

```python
# List meetings
meetings = client.meeting.list()

# Get meeting details
meeting = client.meeting.details(meeting_id=123)

# Create a meeting
new_meeting = client.meeting.create(
    title="Weekly Team Meeting",
    attendees=[456, 789]
)

# Delete a meeting
client.meeting.delete(meeting_id=123)

# Get multiple meetings by ID (batch read)
result = client.meeting.get_many([123, 456, 789])
for meeting in result.successful:
    print(f"{meeting.name} - {meeting.meeting_date}")
# Handle any failed retrievals
for error in result.failed:
    print(f"Failed to get meeting: {error.error}")
```

### Todos

```python
# List todos for current user
todos = client.todo.list()

# Create a todo
new_todo = client.todo.create(
    title="Complete project proposal",
    meeting_id=123,
    due_date="2024-12-31"
)

# Complete a todo
client.todo.complete(todo_id=456)

# Update a todo
client.todo.update(
    todo_id=456,
    title="Updated title",
    due_date="2024-12-25"
)
```

### Goals (Rocks)

```python
# List goals
goals = client.goal.list()

# Create a goal
new_goal = client.goal.create(
    title="Increase sales by 20%",
    meeting_id=123,
    user_id=456
)

# Update goal status
client.goal.update(goal_id=789, status="on")  # on, off, or complete

# Archive a goal
client.goal.archive(goal_id=789)
```

### Scorecard

```python
# Get current week
week = client.scorecard.current_week()

# List scorecard items
scorecards = client.scorecard.list(meeting_id=123)

# Update a score
client.scorecard.score(measurable_id=456, score=95.5)
```

### Issues

```python
# List issues
issues = client.issue.list()

# Create an issue
new_issue = client.issue.create(
    meeting_id=123,
    title="Server performance degradation"
)

# Solve an issue
client.issue.solve(issue_id=456)
```

### Headlines

```python
# List headlines
headlines = client.headline.list(meeting_id=123)

# Create a headline
new_headline = client.headline.create(
    meeting_id=123,
    title="Product launch successful",
    notes="Exceeded targets by 15%"
)

# Update a headline
client.headline.update(headline_id=456, title="Updated headline")

# Delete a headline
client.headline.delete(headline_id=456)
```

## Configuration

The SDK supports multiple ways to provide your API key:

1. **Direct initialization**: Pass the API key when creating the client
2. **Environment variable**: Set `BG_API_KEY` in your environment
3. **Configuration file**: Store the API key in `~/.bloomy/config.yaml`
4. **Dynamic configuration**: Use username/password to fetch and store the API key

```python
# Using configuration file
config = Configuration()
config.configure_api_key("username", "password", store_key=True)
```

## Error Handling

The SDK raises specific exceptions for different error scenarios:

```python
from bloomy.exceptions import BloomyError, ConfigurationError, AuthenticationError, APIError

try:
    client.user.details()
except AuthenticationError:
    print("Invalid API key")
except APIError as e:
    print(f"API error: {e.message}, Status: {e.status_code}")
except BloomyError as e:
    print(f"General error: {e}")
```

## Development

This SDK uses:
- **uv** for package management
- **ruff** for formatting and linting
- **pyright** for type checking
- **pytest** for testing

To set up the development environment:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Run linting
uv run ruff check . --fix

# Type checking
uv run pyright
```

## Requirements

- Python 3.12+
- httpx
- pyyaml
- pydantic
