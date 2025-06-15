# Authentication

The Bloomy SDK uses API key authentication for all requests to the Bloom Growth API.

## Obtaining an API Key

You can obtain an API key using the Token endpoint:

```bash
curl -i -X POST -d "grant_type=password" \
  -d "userName=YOUR_USERNAME_HERE" \
  -d "password=YOUR_PASSWORD_HERE" \
  'https://app.bloomgrowth.com/Token'
```

The response will include an `access_token` field which is your API key.

### Via SDK (Using Username/Password)

You can also use the SDK to fetch and store your API key:

```python
from bloomy import Configuration

config = Configuration()
config.configure_api_key(
    username="your-email@example.com",
    password="your-password",
    store_key=True
)

# API key is now saved in ~/.bloomy/config.yaml
```

## Authentication Methods

### Method 1: Direct API Key

Pass the API key directly when creating the client:

```python
from bloomy import Client

client = Client(api_key="your-api-key-here")
```

**Pros:**
- Explicit and clear
- Good for scripts and notebooks
- Easy to switch between different keys

**Cons:**
- Risk of exposing keys in code
- Not suitable for shared codebases

### Method 2: Environment Variable

Set the `BG_API_KEY` environment variable:

```bash
export BG_API_KEY="your-api-key-here"
```

Use the client without parameters:

```python
from bloomy import Client

client = Client()  # Uses BG_API_KEY automatically
```

**Pros:**
- Secure for production deployments
- Works well with CI/CD systems
- No hardcoded credentials

**Cons:**
- Requires environment setup
- Less convenient for development

### Method 3: Configuration File

Store credentials in a local config file:

```python
from bloomy import Configuration, Client

# First time setup
config = Configuration()
config.configure_api_key(
    username="your-email@example.com",
    password="your-password",
    store_key=True
)

# Subsequent usage
client = Client()  # Loads from ~/.bloomy/config.yaml
```

**Pros:**
- Convenient for development
- Credentials persist between sessions
- No need to remember API key

**Cons:**
- Not suitable for shared environments
- Requires secure file permissions

## Security Best Practices

### 1. Never Commit Credentials

Add to `.gitignore`:

```gitignore
# Bloomy configuration
.bloomy/
config.yaml

# Environment files
.env
.env.local
```

### 2. Use Environment Variables in Production

```python
# production.py
import os
from bloomy import Client

# Fail fast if not configured
api_key = os.environ.get("BG_API_KEY")
if not api_key:
    raise ValueError("BG_API_KEY environment variable is required")

client = Client(api_key=api_key)
```

### 3. Secure Configuration Files

```bash
# Set restrictive permissions
chmod 600 ~/.bloomy/config.yaml

# Verify permissions
ls -la ~/.bloomy/config.yaml
# Should show: -rw-------
```

### 4. Use Separate Keys for Environments

```python
import os
from bloomy import Client

# Use different keys for different environments
if os.getenv("ENVIRONMENT") == "production":
    api_key = os.getenv("BG_API_KEY_PROD")
else:
    api_key = os.getenv("BG_API_KEY_DEV")

client = Client(api_key=api_key)
```

### 5. Implement Key Rotation

```python
from bloomy import Configuration
import schedule
import time

def rotate_api_key():
    config = Configuration()
    # Fetch new key using current credentials
    config.configure_api_key(
        username=os.getenv("BLOOMY_USERNAME"),
        password=os.getenv("BLOOMY_PASSWORD"),
        store_key=True
    )
    print("API key rotated successfully")

# Schedule monthly rotation
schedule.every(30).days.do(rotate_api_key)
```

## Authentication Headers

The SDK automatically adds the required authentication headers:

```python
# This is handled internally by the SDK
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

## Troubleshooting

### Authentication Failed

```python
from bloomy import Client, APIError

try:
    client = Client(api_key="invalid-key")
    client.user.details()
except APIError as e:
    if e.status_code == 401:
        print("Authentication failed. Check your API key.")
    else:
        print(f"API error: {e}")
```

### Missing API Key

```python
from bloomy import Client, ConfigurationError

try:
    # No API key provided anywhere
    client = Client()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    print("Please provide an API key via parameter, environment variable, or config file")
```

### Debugging Authentication

```python
import os
from bloomy import Configuration

# Check configuration sources
config = Configuration()

print("Configuration debugging:")
print(f"Config file path: {config.config_path}")
print(f"Config file exists: {config.config_path.exists()}")
print(f"Has saved API key: {config.has_api_key()}")
print(f"BG_API_KEY set: {'BG_API_KEY' in os.environ}")
```

## Multi-Account Support

To work with multiple Bloom Growth accounts:

```python
from bloomy import Client

# Create separate clients for different accounts
client_account1 = Client(api_key="api-key-for-account-1")
client_account2 = Client(api_key="api-key-for-account-2")

# Use different clients for different operations
users_account1 = client_account1.user.all()
users_account2 = client_account2.user.all()
```

## Next Steps

- Review [Error Handling](errors.md) for handling authentication errors
- See [Configuration](../getting-started/configuration.md) for detailed setup options
- Check [Basic Usage](usage.md) for making authenticated requests