# Client

The main entry point for interacting with the Bloomy API.

::: bloomy.client.Client
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      members_order: source
      show_signature_annotations: true

## Basic Usage

```python
from bloomy import Client, ConfigurationError

# Initialize with API key
client = Client(api_key="your-api-key")

# Custom base URL (for testing/staging)
client = Client(
    api_key="your-api-key",
    base_url="https://staging.example.com/api/v1"
)

# Custom timeout (in seconds)
client = Client(api_key="your-api-key", timeout=60.0)

# Handle missing API key
try:
    client = Client()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Parameters

- **api_key** (str, optional): Your Bloom Growth API key. If not provided, will attempt to load from `BG_API_KEY` environment variable or `~/.bloomy/config.yaml`
- **base_url** (str, optional): Custom API endpoint. Defaults to `"https://app.bloomgrowth.com/api/v1"`
- **timeout** (float, optional): Request timeout in seconds. Defaults to `30.0`

## Exceptions

- **ConfigurationError**: Raised when no API key can be found from any source

## Context Manager

The Client supports context manager protocol for automatic resource cleanup:

```python
with Client(api_key="your-api-key") as client:
    users = client.user.list()
    # Client automatically closes when exiting the context
```