# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Subagent Delegation (Manager Mode)

**IMPORTANT**: You should act as a manager, delegating implementation work to specialized subagents while focusing on coordination and review.

### Available Subagents

| Subagent | Use For |
|----------|---------|
| `api-feature-developer` | New SDK operations, API features, sync/async implementations |
| `mkdocs-documentation-writer` | Guides, API docs, README updates, changelog |
| `code-quality-reviewer` | Quality gates (ruff, pyright, pytest), code review |
| `sdk-test-engineer` | Writing tests, debugging failures, coverage |
| `version-control-engineer` | Commits, PRs, version bumping, releases |

### Delegation Guidelines

1. **PROACTIVELY delegate** to subagents for their specialized domains
2. **Chain workflows**: e.g., implement feature → write tests → review → commit
3. **Review outputs** rather than implementing directly
4. **Use parallel agents** when tasks are independent (e.g., tests + docs simultaneously)

### Example Workflows

- "Add new API operation" → `api-feature-developer` → `sdk-test-engineer` → `code-quality-reviewer`
- "Document feature" → `mkdocs-documentation-writer` → `code-quality-reviewer`
- "Release new version" → `code-quality-reviewer` → `version-control-engineer`

## Development Commands

```bash
# Install dependencies
uv sync --all-extras

# Run all tests with coverage
uv run pytest

# Run a single test file
uv run pytest tests/test_users.py

# Run a specific test
uv run pytest tests/test_users.py::test_user_details -v

# Format code
uv run ruff format .

# Lint and auto-fix
uv run ruff check . --fix

# Type checking (strict mode)
uv run pyright

# Build documentation
uv run mkdocs serve
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
   - Sync operations in `src/bloomy/operations/` inherit from `BaseOperations`
   - Async operations in `src/bloomy/operations/async_/` inherit from `AsyncBaseOperations`
   - Both inherit from `AbstractOperations` which provides shared logic
   - Operations are accessed via client attributes: `client.user`, `client.meeting`, etc.

4. **Models (`src/bloomy/models.py`)**:
   - Pydantic models for type-safe API responses
   - All models inherit from `BloomyBaseModel` with common config
   - Field aliases map PascalCase API responses to snake_case Python attributes

5. **API Endpoints**:
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

4. **Type Annotations**: Uses Python 3.12+ union syntax (`|`) and Pydantic models for structured return types.

5. **Testing**: Mock-based testing with `unittest.mock`. Fixtures in `tests/conftest.py` provide sample data and mock HTTP client. Use `pytest-asyncio` for async tests.

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
