# AsyncClient

::: bloomy.AsyncClient
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false
      members:
        - __init__
        - __aenter__
        - __aexit__
        - close
      heading_level: 2

## Basic Usage

```python
import asyncio
from bloomy import AsyncClient, ConfigurationError

async def main():
    # Initialize with API key
    async with AsyncClient(api_key="your-api-key") as client:
        users = await client.user.list()

    # Custom base URL (for testing/staging)
    async with AsyncClient(
        api_key="your-api-key",
        base_url="https://staging.example.com/api/v1"
    ) as client:
        users = await client.user.list()

    # Custom timeout (in seconds)
    async with AsyncClient(api_key="your-api-key", timeout=60.0) as client:
        users = await client.user.list()

    # Handle missing API key
    try:
        client = AsyncClient()
    except ConfigurationError as e:
        print(f"Configuration error: {e}")

asyncio.run(main())
```

## Parameters

- **api_key** (str, optional): Your Bloom Growth API key. If not provided, will attempt to load from `BG_API_KEY` environment variable or `~/.bloomy/config.yaml`
- **base_url** (str, optional): Custom API endpoint. Defaults to `"https://app.bloomgrowth.com/api/v1"`
- **timeout** (float, optional): Request timeout in seconds. Defaults to `30.0`

## Exceptions

- **ConfigurationError**: Raised when no API key can be found from any source

## Context Manager

The AsyncClient supports async context manager protocol for automatic resource cleanup:

```python
async with AsyncClient(api_key="your-api-key") as client:
    users = await client.user.list()
    # Client automatically closes when exiting the context
```