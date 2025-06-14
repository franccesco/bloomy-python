# Configuration

The Bloomy SDK provides flexible configuration options to suit different use cases and deployment scenarios.

## Configuration Methods

### 1. Direct API Key

The simplest method - pass your API key directly to the client:

```python
from bloomy import Client

client = Client(api_key="your-api-key-here")
```

**Best for**: Scripts, notebooks, and testing

### 2. Environment Variable

Set the `BLOOMY_API_KEY` environment variable:

```bash
# Linux/macOS
export BLOOMY_API_KEY="your-api-key-here"

# Windows
set BLOOMY_API_KEY=your-api-key-here
```

Then initialize the client without parameters:

```python
from bloomy import Client

client = Client()  # Automatically uses BLOOMY_API_KEY
```

**Best for**: Production applications, CI/CD pipelines

### 3. Configuration File

The SDK can store credentials in a local configuration file:

```python
from bloomy import Configuration

# Initial setup - fetches and saves API key
config = Configuration()
config.configure(
    username="your-email@example.com",
    password="your-password"
)

# Future usage - automatically loads saved API key
from bloomy import Client
client = Client()
```

The configuration is stored in `~/.bloomy/config.yaml`:

```yaml
api_key: your-api-key-here
```

**Best for**: Development environments, personal use

## Configuration Priority

When initializing a client, the SDK checks for credentials in this order:

1. Direct `api_key` parameter
2. `BLOOMY_API_KEY` environment variable
3. Configuration file (`~/.bloomy/config.yaml`)

The first valid API key found is used.

## Managing Configuration

### View Current Configuration

```python
from bloomy import Configuration

config = Configuration()
print(f"Config file: {config.config_path}")
print(f"Has API key: {config.has_api_key()}")
```

### Update Configuration

```python
# Update with new credentials
config.configure(
    username="new-email@example.com",
    password="new-password"
)

# Or set API key directly
config.api_key = "new-api-key"
config.save()
```

### Clear Configuration

```python
# Remove stored credentials
config.clear()
```

## Custom Base URL

For testing or using a different API endpoint:

```python
client = Client(
    api_key="your-api-key",
    base_url="https://custom-api.example.com/api/v1"
)
```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** in production
3. **Restrict file permissions** on config files:
   ```bash
   chmod 600 ~/.bloomy/config.yaml
   ```
4. **Rotate API keys** regularly
5. **Use separate keys** for development and production

## Troubleshooting

### Missing API Key Error

If you see `BloomyError: No API key provided`, check:

1. Spelling of environment variable (`BLOOMY_API_KEY`)
2. Configuration file exists at `~/.bloomy/config.yaml`
3. API key is properly formatted

### Authentication Failed

If authentication fails:

1. Verify API key is correct and active
2. Check if your account has API access enabled
3. Ensure you're using the correct base URL

### Configuration File Issues

To reset configuration:

```bash
rm -rf ~/.bloomy
```

Then reconfigure using the Configuration class.