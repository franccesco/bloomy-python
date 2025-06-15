# Quick Start

This guide will help you get started with the Bloomy Python SDK in just a few minutes.

## Step 1: Get Your API Key

First, you'll need an API key from Bloom Growth. You can obtain it using the Token endpoint:

```bash
curl -i -X POST -d "grant_type=password" \
  -d "userName=YOUR_USERNAME_HERE" \
  -d "password=YOUR_PASSWORD_HERE" \
  'https://app.bloomgrowth.com/Token'
```

The response will include an `access_token` field which is your API key.

## Step 2: Configure Authentication

There are three ways to provide your API key:

### Option 1: Direct Initialization (Recommended for Scripts)

```python
from bloomy import Client

client = Client(api_key="your-api-key-here")
```

### Option 2: Environment Variable (Recommended for Applications)

Set the environment variable:

```bash
export BG_API_KEY="your-api-key-here"
```

Then initialize without parameters:

```python
from bloomy import Client

client = Client()
```

### Option 3: Configuration File (Recommended for Development)

Save your credentials using the configuration helper:

```python
from bloomy import Configuration

# Save credentials
config = Configuration()
config.configure_api_key(
    username="your-email@example.com",
    password="your-password",
    store_key=True
)

# Now you can use the client without any parameters
from bloomy import Client
client = Client()
```

## Step 3: Make Your First API Call

Let's verify everything is working by fetching your user information:

```python
from bloomy import Client

# Initialize client
client = Client(api_key="your-api-key")

# Get current user
me = client.user.details()
print(f"Logged in as: {me.name}")

# List your meetings
meetings = client.meeting.list()
print(f"\nYou have {len(meetings)} meetings:")
for meeting in meetings[:5]:  # Show first 5
    print(f"  - {meeting.name}")
```

## Step 4: Explore Common Operations

### Working with Todos

```python
# List your todos
todos = client.todo.list()
open_todos = [t for t in todos if not t.complete]
print(f"You have {len(open_todos)} open todos")

# Create a new todo (requires meeting_id)
meeting_id = meetings[0].id
new_todo = client.todo.create(
    title="Complete quarterly review",
    meeting_id=meeting_id,
    due_date="2024-12-31",
    notes="Review all Q4 metrics and prepare summary"
)
print(f"Created todo: {new_todo.name} (ID: {new_todo.id})")
```

### Working with Goals (Rocks)

```python
# List your active goals
goals = client.goal.list()
for goal in goals:
    print(f"Goal: {goal.title} - {goal.status}")

# Create a new goal (requires meeting_id)
meeting_id = meetings[0].id
new_goal = client.goal.create(
    title="Launch new product feature",
    meeting_id=meeting_id
)
```

### Working with Meetings

```python
# Get a specific meeting's details
meeting_id = meetings[0].id
meeting = client.meeting.details(meeting_id)

# Get meeting attendees
attendees = client.meeting.attendees(meeting_id)
print(f"Meeting has {len(attendees)} attendees")

# Add a headline to the meeting
headline = client.headline.create(
    meeting_id=meeting_id,
    title="Team exceeded Q4 sales target by 15%",
    notes="Great job everyone!"
)
```

## Using Context Managers

The client supports context managers for automatic resource cleanup:

```python
from bloomy import Client

with Client(api_key="your-api-key") as client:
    user = client.user.details()
    meetings = client.meeting.list()
    # Client automatically closes when exiting the context
```

## Error Handling

Always handle potential errors when making API calls:

```python
from bloomy import Client, BloomyError, APIError

client = Client(api_key="your-api-key")

try:
    user = client.user.details()
except APIError as e:
    print(f"API error: {e} (Status: {e.status_code})")
except BloomyError as e:
    print(f"SDK error: {e}")
```

## Next Steps

- Read the [Configuration Guide](configuration.md) for more authentication options
- Explore the [API Reference](../api/client.md) for all available operations
- Check out the [User Guide](../guide/usage.md) for advanced usage patterns