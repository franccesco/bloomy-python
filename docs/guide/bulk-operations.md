# Bulk Operations

The Bloomy SDK provides bulk operations for efficiently working with multiple resources at once. These methods use a best-effort approach, processing items sequentially to avoid rate limiting while capturing both successful and failed operations.

## Overview

Bulk operations are available for:

**Creation:**
- Issues
- Todos
- Meetings
- Goals (Rocks)

**Reading:**
- Meetings (batch retrieve by ID)

Each bulk operation returns a `BulkCreateResult` containing:

- `successful`: List of successfully processed items (created or retrieved)
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

## Batch Reading Operations

### Retrieving Multiple Meetings

The SDK supports batch retrieval of meetings by ID, which is useful when you need details for multiple meetings:

```python
# Get details for multiple meetings
meeting_ids = [123, 456, 789, 999]  # IDs to retrieve
result = client.meeting.get_many(meeting_ids)

# Process successful retrievals
print(f"Successfully retrieved {len(result.successful)} meetings:")
for meeting in result.successful:
    print(f"  - {meeting.name} on {meeting.meeting_date}")
    print(f"    Attendees: {len(meeting.attendees)}")
    print(f"    Todos: {len(meeting.todos)}")
    print(f"    Issues: {len(meeting.issues)}")

# Handle failed retrievals
if result.failed:
    print(f"\nFailed to retrieve {len(result.failed)} meetings:")
    for failure in result.failed:
        meeting_id = failure.input_data.get('meeting_id')
        print(f"  - Meeting ID {meeting_id}: {failure.error}")
```

### Use Cases for Batch Reading

```python
# Example 1: Get details for all meetings from a list operation
meetings_list = client.meeting.list()
meeting_ids = [m.id for m in meetings_list[:10]]  # First 10 meetings

result = client.meeting.get_many(meeting_ids)
meetings_with_details = result.successful

# Example 2: Aggregate data across multiple meetings
def get_all_open_issues(meeting_ids):
    """Get all open issues from multiple meetings."""
    result = client.meeting.get_many(meeting_ids)
    
    all_issues = []
    for meeting in result.successful:
        open_issues = [issue for issue in meeting.issues if not issue.closed]
        all_issues.extend(open_issues)
    
    return all_issues

# Example 3: Build a dashboard with meeting metrics
def build_meeting_dashboard(meeting_ids):
    """Build dashboard data for multiple meetings."""
    result = client.meeting.get_many(meeting_ids)
    
    dashboard = {
        'total_meetings': len(result.successful),
        'total_attendees': sum(len(m.attendees) for m in result.successful),
        'total_todos': sum(len(m.todos) for m in result.successful),
        'total_open_issues': sum(
            len([i for i in m.issues if not i.closed]) 
            for m in result.successful
        ),
        'failed_retrievals': len(result.failed)
    }
    
    return dashboard
```

!!! note "Performance Considerations"
    The `get_many()` method fetches full meeting details including attendees, issues, todos, and metrics for each meeting. For large batches, this can be data-intensive. Consider chunking if retrieving many meetings.

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

## Async Bulk Operations

The Bloomy SDK provides async versions of all bulk operations, enabling concurrent execution for significantly better performance when processing multiple items.

### Benefits of Async Bulk Operations

- **Concurrent Execution**: Process multiple items simultaneously instead of sequentially
- **Better Performance**: Reduce total execution time by up to 80% for large batches
- **Rate Limit Control**: Use `max_concurrent` parameter to control request parallelism
- **Same Error Handling**: Uses the same `BulkCreateResult` structure as sync operations

### Async Todos Example

```python
import asyncio
from bloomy import AsyncClient
from datetime import datetime, timedelta

async def create_todos_async():
    async with AsyncClient(api_key="your-api-key") as client:
        # Prepare todos
        todos = [
            {
                "meeting_id": 123,
                "title": f"Task {i}",
                "due_date": (datetime.now() + timedelta(days=i)).date().isoformat()
            }
            for i in range(1, 21)  # Create 20 todos
        ]
        
        # Create with controlled concurrency
        result = await client.todo.create_many(todos, max_concurrent=10)
        
        print(f"Created {len(result.successful)} todos concurrently")
        if result.failed:
            print(f"Failed: {len(result.failed)}")

# Run the async function
asyncio.run(create_todos_async())
```

### Async Issues Example

```python
async def bulk_create_issues():
    async with AsyncClient(api_key="your-api-key") as client:
        issues = [
            {
                "meeting_id": 123,
                "title": f"Issue {i}: Performance concern",
                "notes": f"Details about issue {i}"
            }
            for i in range(1, 11)
        ]
        
        # Higher concurrency for smaller payloads
        result = await client.issue.create_many(issues, max_concurrent=15)
        
        # Process results
        for issue in result.successful:
            print(f"Created issue: {issue.title} (ID: {issue.id})")
```

### Async Goals Example

```python
async def create_quarterly_goals():
    async with AsyncClient(api_key="your-api-key") as client:
        # Different goals for team members
        team_goals = []
        for user_id in [456, 789, 101, 112]:
            team_goals.extend([
                {
                    "meeting_id": 123,
                    "title": f"Q1 Goal for User {user_id}",
                    "user_id": user_id
                }
            ])
        
        # Conservative concurrency for complex operations
        result = await client.goal.create_many(team_goals, max_concurrent=5)
        
        return result
```

### Async Meetings Example

```python
async def setup_recurring_meetings():
    async with AsyncClient(api_key="your-api-key") as client:
        # Create a month of weekly meetings
        meetings = [
            {
                "title": f"Week {week} Team Sync",
                "attendees": [456, 789, 321]
            }
            for week in range(1, 5)
        ]
        
        # Create meetings concurrently
        create_result = await client.meeting.create_many(meetings, max_concurrent=5)
        
        # Then fetch all details concurrently
        meeting_ids = [m['id'] for m in create_result.successful]
        details_result = await client.meeting.get_many(meeting_ids, max_concurrent=10)
        
        return details_result.successful
```

### Controlling Concurrency with max_concurrent

The `max_concurrent` parameter controls how many requests can be in flight simultaneously:

```python
async def demonstrate_concurrency_control():
    async with AsyncClient(api_key="your-api-key") as client:
        todos = [{"title": f"Todo {i}", "meeting_id": 123} for i in range(100)]
        
        # Conservative: 3 concurrent requests (slower but safer)
        result_conservative = await client.todo.create_many(todos, max_concurrent=3)
        
        # Moderate: 10 concurrent requests (balanced)
        result_moderate = await client.todo.create_many(todos, max_concurrent=10)
        
        # Aggressive: 20 concurrent requests (faster but may hit rate limits)
        result_aggressive = await client.todo.create_many(todos, max_concurrent=20)
```

!!! tip "Choosing max_concurrent"
    - **Small payloads** (todos, issues): 10-20 concurrent requests
    - **Complex operations** (meetings with attendees): 5-10 concurrent requests
    - **Rate-limited environments**: 3-5 concurrent requests
    - **Default value**: 5 (conservative and safe)

### Error Handling with Async Bulk Operations

Error handling works the same as sync operations but with async/await syntax:

```python
async def robust_bulk_create():
    async with AsyncClient(api_key="your-api-key") as client:
        todos = [
            {"title": "Valid todo", "meeting_id": 123},
            {"title": "Missing meeting_id"},  # Will fail
            {"title": "Another valid todo", "meeting_id": 123}
        ]
        
        result = await client.todo.create_many(todos)
        
        # Handle successes
        successful_ids = [todo.id for todo in result.successful]
        print(f"Successfully created todos: {successful_ids}")
        
        # Handle failures
        for failure in result.failed:
            print(f"Failed at index {failure.index}: {failure.error}")
            print(f"Failed data: {failure.input_data}")
            
            # Optionally retry with corrected data
            if "meeting_id" in failure.error:
                corrected = {**failure.input_data, "meeting_id": 123}
                retry_result = await client.todo.create(**corrected)
```

### Performance Comparison: Async vs Sync

Here's a practical example comparing async and sync performance:

```python
import asyncio
import time
from bloomy import Client, AsyncClient

def sync_bulk_create(todos_data):
    """Synchronous bulk creation."""
    start = time.time()
    
    with Client(api_key="your-api-key") as client:
        result = client.todo.create_many(todos_data)
    
    duration = time.time() - start
    return result, duration

async def async_bulk_create(todos_data, max_concurrent=10):
    """Asynchronous bulk creation."""
    start = time.time()
    
    async with AsyncClient(api_key="your-api-key") as client:
        result = await client.todo.create_many(todos_data, max_concurrent=max_concurrent)
    
    duration = time.time() - start
    return result, duration

# Compare performance
async def performance_comparison():
    # Create test data
    todos_data = [
        {"title": f"Todo {i}", "meeting_id": 123}
        for i in range(50)
    ]
    
    # Run sync version
    sync_result, sync_time = sync_bulk_create(todos_data)
    
    # Run async version
    async_result, async_time = await async_bulk_create(todos_data)
    
    print(f"Sync version: {sync_time:.2f} seconds")
    print(f"Async version: {async_time:.2f} seconds")
    print(f"Speed improvement: {(sync_time / async_time - 1) * 100:.0f}%")

# Run comparison
asyncio.run(performance_comparison())
```

!!! note "Typical Performance Gains"
    - 10 items: 50-60% faster with async
    - 50 items: 70-80% faster with async
    - 100+ items: 80-85% faster with async (diminishing returns due to rate limiting)

### Combining Multiple Async Bulk Operations

```python
async def complete_meeting_setup():
    """Set up a complete meeting with all components."""
    async with AsyncClient(api_key="your-api-key") as client:
        # Create meeting first
        meeting_result = await client.meeting.create_many([
            {"title": "Q1 Planning Session", "attendees": [456, 789]}
        ])
        
        if not meeting_result.successful:
            return None
            
        meeting_id = meeting_result.successful[0]['id']
        
        # Create all meeting components concurrently
        todos_task = client.todo.create_many([
            {"title": "Prepare Q1 roadmap", "meeting_id": meeting_id},
            {"title": "Review budget allocation", "meeting_id": meeting_id}
        ])
        
        issues_task = client.issue.create_many([
            {"title": "Resource constraints", "meeting_id": meeting_id},
            {"title": "Timeline concerns", "meeting_id": meeting_id}
        ])
        
        goals_task = client.goal.create_many([
            {"title": "Complete product launch", "meeting_id": meeting_id},
            {"title": "Achieve 20% growth", "meeting_id": meeting_id}
        ])
        
        # Wait for all operations to complete
        todos_result, issues_result, goals_result = await asyncio.gather(
            todos_task, issues_task, goals_task
        )
        
        print(f"Meeting {meeting_id} setup complete:")
        print(f"  - Todos: {len(todos_result.successful)}")
        print(f"  - Issues: {len(issues_result.successful)}")
        print(f"  - Goals: {len(goals_result.successful)}")
        
        return meeting_id

# Run the setup
asyncio.run(complete_meeting_setup())
```

## Best Practices

1. **Validate Input Data**: Check required fields before bulk operations
2. **Handle Partial Failures**: Always check both successful and failed results
3. **Log Operations**: Keep records of bulk operations for debugging
4. **Use Appropriate Chunk Sizes**: Balance between efficiency and rate limits
5. **Implement Retry Logic**: For transient failures, consider retrying
6. **Monitor Rate Limits**: Watch for 429 errors and adjust accordingly
7. **Choose Async When Appropriate**: Use async for better performance with multiple items
8. **Control Concurrency**: Adjust `max_concurrent` based on your use case and API limits

## Next Steps

- Learn about [Error Handling](errors.md) for bulk operations
- Explore [Async Support](async.md) for concurrent operations
- Review individual resource documentation in the [API Reference](../api/client.md)