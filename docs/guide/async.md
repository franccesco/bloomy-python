# Async Support

The Bloomy Python SDK provides full async/await support through the `AsyncClient` class, enabling non-blocking I/O operations and better performance in async Python applications.

## When to Use Async

Use the `AsyncClient` when:

- Building web applications with async frameworks (FastAPI, Starlette, aiohttp)
- Making multiple API calls that can run concurrently
- Integrating with other async libraries
- Building high-performance data pipelines
- Working in Jupyter notebooks with async support

Use the regular `Client` when:

- Writing simple scripts
- Working in environments that don't support async
- Making occasional API calls
- Prototyping or testing

## Basic Usage

### Initialization

```python
import asyncio
from bloomy import AsyncClient

async def main():
    # Create client with context manager (recommended)
    async with AsyncClient(api_key="your-api-key") as client:
        user = await client.user.details()
        print(user.name)

    # Or create client manually
    client = AsyncClient(api_key="your-api-key")
    user = await client.user.details()
    await client.close()  # Don't forget to close!

asyncio.run(main())
```

### Making API Calls

All methods that make API calls are async and must be awaited:

```python
async with AsyncClient(api_key="your-api-key") as client:
    # User operations
    user = await client.user.details()
    users = await client.user.search("john")
    
    # Meeting operations
    meetings = await client.meeting.list()
    meeting_details = await client.meeting.details(meeting_id)
    
    # Todo operations
    todos = await client.todo.list()
    new_todo = await client.todo.create(
        title="Review async code",
        meeting_id=meeting_id
    )
    
    # Goal operations
    goals = await client.goal.list()
    new_goal = await client.goal.create(
        title="Complete Q1 objectives",
        meeting_id=meeting_id
    )
    
    # Headline operations
    headlines = await client.headline.list()
    new_headline = await client.headline.create(
        meeting_id=meeting_id,
        title="Product launch successful"
    )
    
    # Issue operations
    issues = await client.issue.list()
    new_issue = await client.issue.create(
        meeting_id=meeting_id,
        title="Server performance degradation"
    )
    
    # Scorecard operations
    scorecards = await client.scorecard.list()
    current_week = await client.scorecard.current_week()
```

## Concurrent Operations

One of the main benefits of async is the ability to run multiple operations concurrently:

### Using asyncio.gather()

```python
import asyncio
from bloomy import AsyncClient

async def fetch_all_data(client: AsyncClient):
    # Run multiple operations concurrently
    user, meetings, todos = await asyncio.gather(
        client.user.details(),
        client.meeting.list(),
        client.todo.list()
    )
    
    return {
        "user": user,
        "meetings": meetings,
        "todos": todos
    }

async def main():
    async with AsyncClient(api_key="your-api-key") as client:
        data = await fetch_all_data(client)
        print(f"User: {data['user'].name}")
        print(f"Meetings: {len(data['meetings'])}")
        print(f"Todos: {len(data['todos'])}")

asyncio.run(main())
```

### Using asyncio.create_task()

```python
async def process_meetings(client: AsyncClient):
    # Create tasks for concurrent execution
    meetings = await client.meeting.list()
    
    # Fetch details for all meetings concurrently
    tasks = [
        asyncio.create_task(client.meeting.details(m.id))
        for m in meetings[:5]  # Limit to first 5
    ]
    
    meeting_details = await asyncio.gather(*tasks)
    return meeting_details
```

## Performance Benefits

The async client particularly shines with operations that make multiple API calls:

```python
# Sync version - sequential calls
def get_meeting_summary_sync(client, meeting_id):
    meeting = client.meeting.details(meeting_id)  # Makes 5 API calls sequentially
    return meeting

# Async version - parallel calls
async def get_meeting_summary_async(client, meeting_id):
    meeting = await client.meeting.details(meeting_id)  # Makes 5 API calls in parallel
    return meeting
```

The `meeting.details()` method internally fetches:
- Meeting list (to find the specific meeting)
- Attendees
- Issues
- Todos
- Metrics

With the async client, these sub-requests run concurrently, significantly reducing total execution time.

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from bloomy import AsyncClient

app = FastAPI()

# Dependency to get client
async def get_client():
    async with AsyncClient(api_key="your-api-key") as client:
        yield client

@app.get("/user")
async def get_user(client: AsyncClient = Depends(get_client)):
    user = await client.user.details()
    return {"name": user.name, "id": user.id}

@app.get("/meetings")
async def get_meetings(client: AsyncClient = Depends(get_client)):
    meetings = await client.meeting.list()
    return [{"id": m.id, "name": m.name} for m in meetings]
```

### Bulk Operations

```python
async def bulk_create_todos(client: AsyncClient, todos_data: list[dict]):
    """Create multiple todos concurrently."""
    tasks = [
        asyncio.create_task(
            client.todo.create(
                title=data["title"],
                meeting_id=data["meeting_id"],
                due_date=data.get("due_date")
            )
        )
        for data in todos_data
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle results and errors
    successful = []
    failed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed.append((todos_data[i], str(result)))
        else:
            successful.append(result)
    
    return successful, failed
```

### Data Pipeline Example

```python
async def sync_user_data(client: AsyncClient):
    """Sync all user data efficiently."""
    # Get all users
    all_users = await client.user.list()

    # Process users in batches to avoid overwhelming the API
    batch_size = 10
    user_details = []

    for i in range(0, len(all_users), batch_size):
        batch = all_users[i:i + batch_size]
        batch_tasks = [
            asyncio.create_task(client.user.details(user.id))
            for user in batch
        ]
        batch_results = await asyncio.gather(*batch_tasks)
        user_details.extend(batch_results)

    return user_details
```

## Error Handling

Error handling in async code follows the same patterns as sync code:

```python
from bloomy import AsyncClient, APIError, BloomyError

async def safe_operation(client: AsyncClient):
    try:
        user = await client.user.details()
        return user
    except APIError as e:
        print(f"API error: {e} (Status: {e.status_code})")
        return None
    except BloomyError as e:
        print(f"SDK error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

## Best Practices

1. **Always use context managers** when possible to ensure proper cleanup
2. **Limit concurrency** to avoid overwhelming the API server
3. **Handle errors gracefully** in concurrent operations
4. **Use timeouts** for long-running operations
5. **Consider rate limiting** when making many concurrent requests

```python
import asyncio
from bloomy import AsyncClient

# Good: Limited concurrency
async def process_with_limit(client: AsyncClient, items: list, limit: int = 5):
    semaphore = asyncio.Semaphore(limit)
    
    async def process_item(item):
        async with semaphore:
            return await client.todo.details(item.id)
    
    tasks = [process_item(item) for item in items]
    return await asyncio.gather(*tasks)
```

## Jupyter Notebook Support

The async client works well in Jupyter notebooks with IPython 7.0+:

```python
# In a Jupyter cell
from bloomy import AsyncClient

client = AsyncClient(api_key="your-api-key")
user = await client.user.details()
print(user.name)

# Don't forget to close when done
await client.close()
```

## Migration from Sync to Async

Migrating from sync to async is straightforward:

1. Replace `Client` with `AsyncClient`
2. Add `async` to function definitions
3. Add `await` before all API calls
4. Use `async with` for context managers

```python
# Before (sync)
from bloomy import Client

def get_user_info():
    with Client(api_key="key") as client:
        user = client.user.details()
        return user.name

# After (async)
from bloomy import AsyncClient

async def get_user_info():
    async with AsyncClient(api_key="key") as client:
        user = await client.user.details()
        return user.name
```