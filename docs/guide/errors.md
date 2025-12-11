# Error Handling

The Bloomy SDK provides a comprehensive error handling system to help you gracefully handle API failures and other exceptions.

## Exception Hierarchy

```
BloomyError (base exception)
├── APIError (HTTP errors from API)
├── AuthenticationError (authentication failures)
└── ConfigurationError (configuration issues)
```

## Common Exceptions

### BloomyError

Base exception for all SDK errors:

```python
from bloomy import Client, BloomyError

try:
    client = Client(api_key="your-api-key")
    user = client.user.details()
except BloomyError as e:
    print(f"Bloomy SDK error: {e}")
```

### APIError

Raised when the API returns an error response:

```python
from bloomy import Client, APIError

try:
    client = Client(api_key="invalid-key")
    user = client.user.details()
except APIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
```

**Attributes:**
- `status_code`: The HTTP status code (e.g., 404, 500)
- Message accessed via `str(e)` or just `e` in f-strings

### AuthenticationError

Raised when username/password authentication fails:

```python
from bloomy import Configuration, AuthenticationError

try:
    config = Configuration()
    config.configure_api_key(
        username="invalid-user",
        password="wrong-password"
    )
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

### ConfigurationError

Raised when there are configuration issues:

```python
from bloomy import Client, ConfigurationError

try:
    # No API key provided anywhere
    client = Client()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## HTTP Status Codes

Common status codes and their meanings:

```python
from bloomy import Client, APIError

client = Client(api_key="your-api-key")

try:
    result = client.user.details(user_id=99999)
except APIError as e:
    match e.status_code:
        case 400:
            print("Bad request - check your parameters")
        case 401:
            print("Unauthorized - check your API key")
        case 403:
            print("Forbidden - you don't have permission")
        case 404:
            print("Not found - resource doesn't exist")
        case 429:
            print("Rate limited - too many requests")
        case 500:
            print("Server error - try again later")
        case _:
            print(f"Unexpected error: {e.status_code}")
```

## Error Handling Patterns

### Basic Try-Except

```python
from bloomy import Client, APIError, ConfigurationError

try:
    client = Client()
    users = client.user.list()
except ConfigurationError:
    print("Please configure your API key")
except APIError as e:
    print(f"API request failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Specific Error Handling

```python
def get_user_safely(client, user_id):
    try:
        return client.user.details(user_id)
    except APIError as e:
        if e.status_code == 404:
            return None  # User not found
        raise  # Re-raise other errors

# Usage
user = get_user_safely(client, 12345)
if user:
    print(f"Found user: {user.name}")
else:
    print("User not found")
```

### Retry Logic

Implement exponential backoff for transient failures:

```python
import time
from bloomy import Client, APIError

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except APIError as e:
            last_exception = e
            if e.status_code >= 500 or e.status_code == 429:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
            raise
    
    raise last_exception

# Usage
client = Client(api_key="your-api-key")
users = retry_with_backoff(lambda: client.user.list())
```

### Graceful Degradation

```python
from bloomy import Client, APIError
import logging

logger = logging.getLogger(__name__)

class BloomyService:
    def __init__(self, api_key):
        self.client = Client(api_key=api_key)
        self._cached_user = None
    
    def get_current_user(self):
        try:
            self._cached_user = self.client.user.details()
            return self._cached_user
        except APIError as e:
            logger.error(f"Failed to fetch user: {e}")
            if self._cached_user:
                logger.info("Returning cached user data")
                return self._cached_user
            raise
```

## Validation Errors

Validate inputs before making API calls:

```python
from datetime import datetime
from bloomy import Client

def create_todo_validated(client, title, due_date=None):
    # Validate title
    if not title or not title.strip():
        raise ValueError("Todo title cannot be empty")
    
    if len(title) > 255:
        raise ValueError("Todo title cannot exceed 255 characters")
    
    # Validate due date
    if due_date:
        try:
            datetime.fromisoformat(due_date)
        except ValueError:
            raise ValueError(f"Invalid date format: {due_date}. Use YYYY-MM-DD")
    
    # Create todo
    return client.todo.create(title=title, due_date=due_date)
```

## Logging Errors

Use logging for better debugging:

```python
import logging
from bloomy import Client, APIError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bloomy_app')

client = Client(api_key="your-api-key")

try:
    users = client.user.list()
    logger.info(f"Successfully fetched {len(users)} users")
except APIError as e:
    logger.error(
        f"API request failed: {e}",
        extra={
            'status_code': e.status_code,
            'error_message': str(e)
        }
    )
    raise
```

## Error Context Managers

Create context managers for error handling:

```python
from contextlib import contextmanager
from bloomy import APIError

@contextmanager
def handle_api_errors(default=None):
    try:
        yield
    except APIError as e:
        if e.status_code == 404 and default is not None:
            return default
        print(f"API Error: {e} (Status: {e.status_code})")
        raise

# Usage
with handle_api_errors(default=[]):
    users = client.user.list()
```

## Best Practices

1. **Always catch specific exceptions** - Don't use bare `except:`
2. **Log errors with context** - Include relevant IDs and parameters
3. **Fail fast in production** - Don't hide critical errors
4. **Implement retries for transient failures** - 5xx and 429 errors
5. **Validate inputs early** - Catch errors before API calls
6. **Provide meaningful error messages** - Help users understand what went wrong
7. **Use error monitoring** - Track errors in production

## Common Error Scenarios

### Rate Limiting

```python
from bloomy import Client, APIError
import time

def handle_rate_limit(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except APIError as e:
            if e.status_code == 429:
                # Wait before retrying (check response headers for Retry-After if available)
                retry_after = 60  # Default wait time
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                raise
```

### Network Timeouts

```python
# The SDK uses httpx which handles timeouts
# You can catch timeout errors:
import httpx
from bloomy import Client

try:
    client = Client(api_key="your-api-key")
    users = client.user.list()
except httpx.TimeoutException:
    print("Request timed out. Please try again.")
```

### Authentication Refresh

```python
from bloomy import Client, APIError, Configuration

def create_client_with_refresh():
    config = Configuration()
    
    def refresh_and_retry(func):
        try:
            return func()
        except APIError as e:
            if e.status_code == 401:
                # Re-authenticate
                config.configure_api_key(
                    username=os.getenv("BLOOMY_USERNAME"),
                    password=os.getenv("BLOOMY_PASSWORD"),
                    store_key=True
                )
                # Create new client with fresh token
                new_client = Client()
                return func.__self__.__class__(new_client)
            raise
    
    return Client()
```