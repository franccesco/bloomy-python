# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup
```bash
# Install dependencies (requires uv)
uv sync --all-extras
```

### Testing
```bash
# Run all tests with coverage
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_users.py

# Run a specific test method
uv run pytest tests/test_users.py::TestUserOperations::test_details_basic

# Run tests with short traceback
uv run pytest -v --tb=short
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Lint and auto-fix issues
uv run ruff check . --fix

# Type checking
uv run pyright
```

## Architecture Overview

### SDK Structure
The Bloomy Python SDK is organized as a client-based architecture where all API operations are accessed through a central `Client` instance. The client handles authentication and provides access to operation-specific classes.

### Key Components

1. **Client (`src/bloomy/client.py`)**: 
   - Central entry point for the SDK
   - Initializes httpx client with authentication headers
   - Creates instances of all operation classes
   - Supports context manager protocol

2. **Configuration (`src/bloomy/configuration.py`)**:
   - Manages API key from multiple sources (direct, env var, config file)
   - Can fetch API key using username/password via `/Token` endpoint
   - Stores configuration in `~/.bloomy/config.yaml`

3. **Operations Pattern**:
   - Each API resource has its own operations class (e.g., `UserOperations`, `MeetingOperations`)
   - All operation classes inherit from `BaseOperations` which provides lazy-loaded user ID
   - Operations are accessed via client attributes: `client.user`, `client.meeting`, etc.

4. **API Endpoints**:
   - Base URL: `https://app.bloomgrowth.com/api/v1`
   - Authentication: Bearer token in Authorization header
   - All responses are JSON

### Important Implementation Details

1. **User ID Handling**: The `BaseOperations` class provides a `user_id` property that lazy-loads the current user's ID from `/users/mine` endpoint. This is used as default in many operations.

2. **Response Transformation**: API responses are transformed into Python dictionaries with snake_case keys. The Ruby API uses PascalCase.

3. **Error Handling**: 
   - Custom exception hierarchy rooted at `BloomyError`
   - `APIError` includes status code
   - HTTP errors are raised via `response.raise_for_status()`

4. **Type Annotations**: Uses Python 3.12+ union syntax (`|`) and TypedDict for structured return types.

5. **Testing**: Mock-based testing with `unittest.mock`. Fixtures defined in `conftest.py` provide sample data and mock HTTP client.

### API Operations Reference

- **Users**: Get details, search, list all users, get direct reports/positions
- **Meetings**: CRUD operations, get attendees/issues/todos/metrics
- **Todos**: CRUD operations for user or meeting todos
- **Goals** (aka Rocks): CRUD operations, archive/restore functionality
- **Scorecard**: Get current week, list/update scores
- **Issues**: Create, list, solve issues
- **Headlines**: CRUD operations for meeting headlines

### Common Patterns

1. **Optional Parameters**: Many list operations accept either `user_id` or `meeting_id` but not both
2. **Default User**: When `user_id` is not provided, operations default to the authenticated user
3. **Include Flags**: Some operations have `include_closed` or similar flags to control filtering