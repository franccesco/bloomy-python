# Bulk Operations

The Bloomy SDK provides bulk creation methods for efficiently creating multiple resources at once. These methods use a best-effort approach, processing items sequentially to avoid rate limiting while capturing both successful and failed operations.

## Overview

Bulk operations are available for:

- Issues
- Todos
- Meetings
- Goals (Rocks)

Each bulk operation returns a `BulkCreateResult` containing:

- `successful`: List of successfully created items
- `failed`: List of `BulkCreateError` objects with failure details

!!! note "Best-Effort Processing"
    Bulk operations are not transactional. If one item fails, the operation continues with the remaining items. Always check both successful and failed results.

## BulkCreateResult Structure

```python
from bloomy.models import BulkCreateResult, BulkCreateError

# Result structure
result = BulkCreateResult(
    successful=[...],  # List of successfully created items
    failed=[           # List of failed operations
        BulkCreateError(
            index=2,                        # Original index in input list
            input_data={"title": "..."},    # Data that failed
            error="Validation error: ..."   # Error message
        )
    ]
)
```

## Creating Multiple Issues

Create multiple issues for a meeting:

```python
# Prepare issue data
issues = [
    {
        "meeting_id": 123,
        "title": "Review Q4 metrics",
        "notes": "Focus on conversion rates"
    },
    {
        "meeting_id": 123,
        "title": "Discuss budget overruns",
        "user_id": 456  # Assign to specific user
    },
    {
        "meeting_id": 123,
        "title": "Customer feedback analysis"
    }
]

# Create issues
result = client.issue.create_many(issues)

# Handle results
print(f"Created {len(result.successful)} issues")
for issue in result.successful:
    print(f"  - {issue.title} (ID: {issue.id})")

if result.failed:
    print(f"\nFailed to create {len(result.failed)} issues:")
    for failure in result.failed:
        print(f"  - Index {failure.index}: {failure.error}")
```

## Creating Multiple Todos

Batch create todos with different assignees and due dates:

```python
from datetime import datetime, timedelta

# Generate due dates
today = datetime.now().date()
tomorrow = (today + timedelta(days=1)).isoformat()
next_week = (today + timedelta(days=7)).isoformat()

# Prepare todos
todos = [
    {
        "meeting_id": 123,
        "title": "Send meeting notes",
        "due_date": tomorrow
    },
    {
        "meeting_id": 123,
        "title": "Update project dashboard",
        "user_id": 456,
        "due_date": next_week,
        "notes": "Include latest metrics"
    },
    {
        "meeting_id": 123,
        "title": "Schedule follow-up meeting"
    }
]

# Create todos
result = client.todo.create_many(todos)

# Process results
if result.successful:
    print(f"Successfully created {len(result.successful)} todos")
    
if result.failed:
    # Handle failures - maybe retry or log
    for failure in result.failed:
        print(f"Failed todo '{failure.input_data['title']}': {failure.error}")
```

## Creating Multiple Goals

Create quarterly goals for team members:

```python
# Quarterly goals for different team members
goals = [
    {
        "meeting_id": 123,
        "title": "Increase NPS score to 70+",
        "user_id": 456
    },
    {
        "meeting_id": 123,
        "title": "Launch mobile app v2.0",
        "user_id": 789
    },
    {
        "meeting_id": 123,
        "title": "Reduce customer churn by 15%"
        # user_id defaults to current user
    }
]

# Create goals
result = client.goal.create_many(goals)

# Report results
print(f"Goal creation summary:")
print(f"  Successful: {len(result.successful)}")
print(f"  Failed: {len(result.failed)}")

# Archive failed goals for review
if result.failed:
    failed_titles = [f.input_data['title'] for f in result.failed]
    print(f"Failed goals: {', '.join(failed_titles)}")
```

## Creating Multiple Meetings

Create a series of meetings:

```python
# Weekly team meetings
meetings = [
    {
        "title": "Weekly Team Sync - Week 1",
        "attendees": [456, 789]  # User IDs
    },
    {
        "title": "Weekly Team Sync - Week 2",
        "attendees": [456, 789, 321]
    },
    {
        "title": "Monthly All-Hands",
        "add_self": True  # Explicitly add current user
    }
]

# Create meetings
result = client.meeting.create_many(meetings)

# Get meeting IDs for further operations
meeting_ids = [m['id'] for m in result.successful]
print(f"Created meetings with IDs: {meeting_ids}")
```

## Error Handling Strategies

### Retry Failed Operations

```python
def retry_failed_items(client, failed_items, resource_type):
    """Retry failed bulk operations."""
    if not failed_items:
        return
    
    # Extract original data from failures
    retry_data = [f.input_data for f in failed_items]
    
    # Retry based on resource type
    if resource_type == "todo":
        retry_result = client.todo.create_many(retry_data)
    elif resource_type == "issue":
        retry_result = client.issue.create_many(retry_data)
    # ... handle other types
    
    return retry_result

# Usage
result = client.todo.create_many(todos)
if result.failed:
    print(f"Retrying {len(result.failed)} failed todos...")
    retry_result = retry_failed_items(client, result.failed, "todo")
```

### Validation Before Bulk Creation

```python
def validate_todos(todos):
    """Pre-validate todos before bulk creation."""
    valid = []
    invalid = []
    
    for i, todo in enumerate(todos):
        errors = []
        
        if "title" not in todo:
            errors.append("Missing required field: title")
        if "meeting_id" not in todo:
            errors.append("Missing required field: meeting_id")
        if len(todo.get("title", "")) > 255:
            errors.append("Title too long (max 255 chars)")
            
        if errors:
            invalid.append((i, todo, errors))
        else:
            valid.append(todo)
    
    return valid, invalid

# Validate before creating
valid_todos, invalid_todos = validate_todos(todos)

if invalid_todos:
    print("Invalid todos found:")
    for idx, todo, errors in invalid_todos:
        print(f"  Index {idx}: {', '.join(errors)}")

# Create only valid todos
if valid_todos:
    result = client.todo.create_many(valid_todos)
```

### Partial Success Handling

```python
def handle_bulk_result(result, resource_name):
    """Generic handler for bulk operation results."""
    total = len(result.successful) + len(result.failed)
    success_rate = len(result.successful) / total * 100 if total > 0 else 0
    
    print(f"\n{resource_name} Bulk Creation Summary:")
    print(f"  Total: {total}")
    print(f"  Successful: {len(result.successful)} ({success_rate:.1f}%)")
    print(f"  Failed: {len(result.failed)}")
    
    if result.failed:
        print(f"\nFailure Details:")
        for failure in result.failed:
            print(f"  - Item {failure.index}: {failure.error}")
            print(f"    Data: {failure.input_data}")
    
    return result.successful, result.failed

# Usage
result = client.issue.create_many(issues)
successful, failed = handle_bulk_result(result, "Issue")
```

## Performance Considerations

!!! warning "Rate Limiting"
    Bulk operations process items sequentially to avoid rate limiting. For large batches, consider:
    
    - Breaking into smaller chunks (e.g., 50-100 items)
    - Adding delays between chunks
    - Monitoring API rate limit headers

### Chunking Large Operations

```python
def chunk_list(items, chunk_size=50):
    """Split list into chunks."""
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]

# Process large batch in chunks
all_todos = [...]  # Large list of todos
all_results = []

for i, chunk in enumerate(chunk_list(all_todos, 50)):
    print(f"Processing chunk {i + 1}...")
    result = client.todo.create_many(chunk)
    all_results.append(result)
    
    # Optional: Add delay between chunks
    if i < len(all_todos) // 50:
        time.sleep(1)

# Aggregate results
total_successful = sum(len(r.successful) for r in all_results)
total_failed = sum(len(r.failed) for r in all_results)
```

## Best Practices

1. **Validate Input Data**: Check required fields before bulk operations
2. **Handle Partial Failures**: Always check both successful and failed results
3. **Log Operations**: Keep records of bulk operations for debugging
4. **Use Appropriate Chunk Sizes**: Balance between efficiency and rate limits
5. **Implement Retry Logic**: For transient failures, consider retrying
6. **Monitor Rate Limits**: Watch for 429 errors and adjust accordingly

## Next Steps

- Learn about [Error Handling](errors.md) for bulk operations
- Explore [Async Support](async.md) for concurrent operations
- Review individual resource documentation in the [API Reference](../api/client.md)