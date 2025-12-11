# Exceptions

Exception classes used throughout the Bloomy SDK.

## Base Exception

::: bloomy.exceptions.BloomyError
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false

## Authentication Errors

::: bloomy.exceptions.AuthenticationError
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false

Raised when username/password authentication fails. This typically occurs when using `Configuration.configure_api_key()` with invalid credentials.

**Example:**

```python
from bloomy import Configuration, AuthenticationError

try:
    config = Configuration()
    config.configure_api_key(
        username="user@example.com",
        password="wrong_password"
    )
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

## API Errors

::: bloomy.exceptions.APIError
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false

## Configuration Errors

::: bloomy.exceptions.ConfigurationError
    options:
      show_source: true
      show_root_heading: true
      show_root_full_path: false