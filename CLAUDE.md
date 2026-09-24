# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Subagent Delegation (Manager Mode)

Act as a manager: delegate implementation work to the project subagents in `.claude/agents/` and spend your own effort on coordination and review. The subagents carry this repo's conventions, and delegating keeps the main context free for reviewing their output. Changes of a line or two are faster to make directly. Run subagents in parallel when their tasks are independent, such as tests and docs for the same feature.

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
uv run pytest tests/test_users.py::TestUserOperations::test_details_basic -v

# Format code
uv run ruff format .

# Lint and auto-fix
uv run ruff check . --fix

# Type checking (strict mode)
uv run basedpyright

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
   - Exposes two namespaces sharing the same httpx client and API key: `client.v1` (the REST API; top-level attributes like `client.user`/`client.meeting` are aliases onto `client.v1.*`, kept for backward compatibility) and `client.v2` (the GraphQL API at `graphql_url`, defaulting to the scheme/host of `base_url` plus `/graphql/`) — see "v2 (GraphQL) Operations Pattern" below

2. **Configuration (`src/bloomy/configuration.py`)**:
   - Manages API key from multiple sources (direct, env var, config file)
   - Can fetch API key using username/password via `/Token` endpoint
   - Stores configuration in `~/.bloomy/config.yaml`

3. **Operations Pattern**:
   - Each API resource has its own operations class (e.g., `UserOperations`, `MeetingOperations`)
   - Sync operations in `src/bloomy/operations/` inherit from `BaseOperations`
   - Async operations in `src/bloomy/operations/async_/` inherit from `AsyncBaseOperations`
   - Both inherit from `AbstractOperations` which provides shared logic
   - Response transformation is handled by mixins in `src/bloomy/operations/mixins/` (e.g., `UserOperationsMixin`, `MeetingOperationsMixin`)
   - Mixins use `_transform` suffix naming convention (e.g., `goals_transform.py`, `users_transform.py`)
   - Generic bulk operations logic is provided in base classes (`_validate_bulk_item`, `_process_bulk_sync`, `_process_bulk_async`)
   - Operations are accessed via client attributes: `client.user`, `client.meeting`, etc.

4. **v2 (GraphQL) Operations Pattern (`src/bloomy/v2/`)**:
   - `client.v2` is the GraphQL namespace, separate from `client.v1`'s REST namespace above; it covers the same entities (users, meetings, issues, headlines, todos, goals, milestones, metrics) through GraphQL documents instead of REST calls
   - Transport and shared helpers live in `src/bloomy/v2/base.py`: module-level functions (`to_timestamp`, `default_due_date`, `compact`, `dig_nodes`, `merge_nodes`), shared field constants (`NOTES_FIELDS`, `USER_REF_FIELDS`, `MEETING_REF_FIELDS`, `MILESTONES_CONNECTION`), and methods on the base classes: `_mutate` (runs a mutation and checks its result), `_one` (reads one entity or raises "not found"), and `_notes_input` (creates the notes pad for a create/edit input). `AbstractGraphQLOperations` subclasses v1's `AbstractOperations`, so meeting_id/user_id checks use `_validate_mutual_exclusion`. One `UserIdCache` per client shares the current user's id across all v2 operations objects
   - Models live in `src/bloomy/v2/models.py`. They inherit `GqlBaseModel`, which validates the raw camelCase keys (field names also work, so `model_dump()` round-trips) and fills `notes` from the notes fields, so operations return `Model.model_validate(raw_node)` with no per-entity transform code
   - Unlike v1, each entity's GraphQL documents, input builders, and sync/async operations classes live together in one module under `src/bloomy/v2/operations/` (e.g. `operations/issue.py` holds `IssueOperationsMixin`, `IssueOperations`, and `AsyncIssueOperations` side by side), instead of v1's separate `operations/`, `operations/async_/`, and `operations/mixins/` directories
   - Each entity module's mixin (`<Entity>OperationsMixin`) holds the GraphQL documents and static builders such as `_todo_list_request`, `_todos_from`, `_todo_create_input`, and `_todo_edit_fields`; the sync and async classes, which inherit it alongside `GraphQLOperations`/`AsyncGraphQLOperations`, only execute and return. Updates and state changes (archive/restore/solve/complete) go through a per-class `_edit(entity_id, fields, *, action)` helper that runs the edit mutation and re-reads the entity (milestones instead delegate `complete()` to `update()`)
   - Operations are accessed via `client.v2.user`, `client.v2.issue`, etc.

5. **Models (`src/bloomy/models.py`)**:
   - Pydantic models for type-safe API responses
   - All models inherit from `BloomyBaseModel` with common config
   - Field aliases map PascalCase API responses to snake_case Python attributes
   - Reusable annotated types: `OptionalDatetime` and `OptionalFloat` using Pydantic's `BeforeValidator`
   - Some models are type aliases for backward compatibility (e.g., `HeadlineListItem = HeadlineDetails`)

6. **API Endpoints**:
   - Base URL: `https://app.bloomgrowth.com/api/v1`
   - Authentication: Bearer token in Authorization header
   - All responses are JSON

### Important Implementation Details

1. **User ID Handling**: The `BaseOperations` class provides a `user_id` property that lazy-loads the current user's ID from `/users/mine` endpoint. This is used as default in many operations.

2. **Response Transformation**: API responses are transformed into Python dictionaries with snake_case keys. The Ruby API uses PascalCase.

3. **Error Handling**:
   - Custom exception hierarchy rooted at `BloomyError`
   - `APIError` includes status code
   - All operations consistently use `response.raise_for_status()` for error handling

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
