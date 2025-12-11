# Installation

## Requirements

The Bloomy Python SDK requires:

- Python 3.12 or higher
- A Bloom Growth account with API access

## Install from PyPI

The recommended way to install the Bloomy SDK is via pip:

```bash
pip install bloomy
```

Or if you're using [uv](https://docs.astral.sh/uv/):

```bash
uv add bloomy
```

## Install from Source

To install the latest development version from GitHub:

```bash
pip install git+https://github.com/franccesco/bloomy-python.git
```

Or clone the repository and install locally:

```bash
git clone https://github.com/franccesco/bloomy-python.git
cd bloomy-python
pip install -e .
```

## Dependencies

The SDK has minimal dependencies:

- `httpx` - Modern HTTP client with async support
- `pyyaml` - For configuration file handling
- `typing-extensions` - For enhanced type hints
- `pydantic` - For data validation and models

All dependencies are automatically installed when you install the SDK.

## Verify Installation

To verify the installation was successful:

```python
import bloomy
print(bloomy.__version__)
```

## Next Steps

Once installed, proceed to the [Quick Start](quickstart.md) guide to configure your API key and make your first API call.