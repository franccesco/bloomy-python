# Basic Usage

This guide covers common usage patterns and best practices for the Bloomy SDK.

## Client Initialization

### Basic Setup

```python
from bloomy import Client

# Initialize with API key
client = Client(api_key="your-api-key")
```

### Using Context Manager

For automatic resource cleanup:

```python
with Client(api_key="your-api-key") as client:
    # Use client here
    users = client.user.list()
# Connection automatically closed
```

## Common Patterns

### Pagination

Many list operations return all results at once. For large datasets, consider filtering:

```python
# Get meetings for specific date range
meetings = client.meeting.list()
recent_meetings = [m for m in meetings if m.id > 0]  # Example filter
```

### Filtering Results

Use Python's built-in filtering capabilities:

```python
# Get only incomplete todos
todos = client.todo.list()
open_todos = [t for t in todos if not t.complete]

# Get issues for a meeting  
issues = client.issue.list(meeting_id=meeting_id)
# Note: Issues don't have a priority field in the API
```

### Working with Dates

The SDK accepts date strings in ISO format:

```python
# Create todo with due date
todo = client.todo.create(
    title="Complete project",
    due_date="2024-12-31"  # YYYY-MM-DD format
)

# Date parsing is handled automatically
from datetime import datetime, timedelta
tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
todo = client.todo.create(
    title="Tomorrow's task",
    due_date=tomorrow
)
```

## Advanced Usage

### Batch Operations

Process multiple items efficiently:

```python
# Complete multiple todos
todos_to_complete = client.todo.list()[:5]
for todo in todos_to_complete:
    if not todo.complete:
        client.todo.complete(todo.id)
```

### Error Recovery

Implement retry logic for transient failures:

```python
import time
from bloomy import APIError

def retry_operation(func, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except APIError as e:
            if e.status_code >= 500 and attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            raise

# Usage
user = retry_operation(lambda: client.user.details())
```

### Custom Headers

Add custom headers if needed:

```python
# Note: This is handled internally, but you can customize the httpx client
client = Client(api_key="your-api-key")
# The client automatically adds Authorization headers
```

## Working with Different Resources

### Users

```python
# Get current user
me = client.user.details()

# Search for users
users = client.user.search("John")

# Get user's direct reports
reports = client.user.direct_reports(user_id=me.id)
```

### Meetings

```python
# List all meetings
meetings = client.meeting.list()

# Get meeting details with participants
meeting_id = meetings[0].id
details = client.meeting.details(meeting_id)
attendees = client.meeting.attendees(meeting_id)

# Get meeting content
todos = client.meeting.todos(meeting_id)
issues = client.meeting.issues(meeting_id)
```

### Goals (Rocks)

```python
# Create a quarterly goal (requires meeting_id)
goal = client.goal.create(
    title="Increase customer satisfaction to 95%",
    meeting_id=meeting_id  # Required parameter
)

# Update goal status
updated = client.goal.update(
    goal_id=goal.id,
    status="complete"  # Options: "on", "off", "at_risk", "complete"
)
print(f"Goal updated: {updated}")  # Returns updated goal dict
```

### Scorecard

```python
# Get current week info
current_week = client.scorecard.current_week()

# Get scorecard items
scorecard_items = client.scorecard.list()

# Update a metric
for item in scorecard_items:
    if item.title == "Sales Calls":
        client.scorecard.score(
            measurable_id=item.measurable_id,
            score=45
        )
```

## Best Practices

1. **Always handle exceptions** - Network calls can fail
2. **Use context managers** - Ensures proper resource cleanup
3. **Cache user ID** - The SDK caches it automatically for operations
4. **Validate inputs** - Check required fields before API calls
5. **Log operations** - Helpful for debugging and auditing

## Performance Tips

1. **Minimize API calls** - Fetch data once and filter locally
2. **Use specific endpoints** - Don't fetch all data if you need one item
3. **Implement caching** - For data that doesn't change frequently
4. **Batch operations** - When updating multiple items

## Next Steps

- Learn about [Error Handling](errors.md)
- Explore the [API Reference](../api/client.md)
- Review [Authentication](authentication.md) options