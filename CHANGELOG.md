# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.19.0] - 2025-12-10

### Fixed

- Made `Position.name` field optional to handle null API responses from Bloom Growth API
- Fixes Pydantic validation errors in `UserOperations.positions()`, `details(include_positions=True)`, and `details(all=True)`

## [0.18.0] - 2025-12-08

### Added

- Async bulk operations with rate limiting for goals, todos, issues, and meetings
- Performance benchmarks documentation for async operations

### Fixed

- Corrected API endpoints and field mappings in async operations

## [0.17.0] - 2025-12-07

### Added

- Batch read operation for meetings via `client.meeting.get_many()`
- Documentation and examples for batch operations

## [0.16.0] - 2025-12-06

### Added

- Claude AI agent configurations and settings for development workflow
- Specialized subagents for manager-mode workflow

### Changed

- Streamlined CLAUDE.md to focus on architecture and development commands

## [0.15.0] - 2025-12-05

### Added

- Comprehensive VS Code devcontainer support for consistent development environment
- GitHub CLI integration in devcontainer

## [0.14.0] - 2025-12-04

### Added

- Bulk creation methods for issues, todos, goals, and meetings
- Comprehensive test suite for bulk operations
- Bulk operations guide documentation

## [0.13.2] - 2025-12-03

### Fixed

- Adjusted scorecard typing expectations

## [0.13.1] - 2025-12-02

### Added

- Comprehensive ruff linting rules with preview features enabled

### Fixed

- All linting issues identified by new ruff rules

## [0.13.0] - 2025-12-01

### Added

- Full async/await support with `AsyncClient`
- Async operations for goals, headlines, issues, and scorecard
- `pytest-asyncio` for async test support

## [0.12.0] - 2025-11-30

### Fixed

- Documentation to match actual SDK implementation
- GitHub/PyPI URLs in documentation
- Authentication guide documentation
- API key retrieval documentation examples

### Removed

- Incorrect licensing information

## [0.11.0] - 2025-11-29

### Added

- Informational badges to README

### Changed

- Simplified API description in documentation

### Removed

- Ruby workflows from GitHub Actions

## [0.10.0] - 2025-11-28

### Fixed

- Documentation and implementation mismatches
- SDK models to match actual API responses
- Client API key initialization priority

## [0.9.0] - 2025-11-27

### Added

- MkDocs documentation with Material theme
- Dynamic version loading from pyproject.toml

### Fixed

- Docstring example formatting for mkdocs
- Documentation to accurately reflect Pydantic model returns

## [0.8.0] - 2025-11-26

### Changed

- Switched to pyright strict mode for enhanced type safety

### Fixed

- All type and linting issues for strict mode compliance

## [0.7.0] - 2025-11-25

### Added

- Pydantic for enhanced data validation and type safety

### Fixed

- Ruff line length configuration
- Pyright TypedDict access issues

### Removed

- Examples folder

## [0.6.0] - 2025-11-24

### Added

- Claude AI instructions for development assistance

## [0.5.0] - 2025-11-23

### Added

- Python version specification in pyproject.toml

### Fixed

- Removed tracked files that should be ignored

## [0.4.0] - 2025-11-22

### Fixed

- All ruff check issues

## [0.1.0] - 2025-11-21

### Added

- Initial Python SDK implementation migrated from Ruby
- Core client with authentication support
- User operations: get details, search, list all users, get direct reports/positions
- Meeting operations: CRUD operations, get attendees/issues/todos/metrics
- Todo operations: CRUD for user or meeting todos
- Goal (Rock) operations: CRUD, archive/restore functionality
- Scorecard operations: get current week, list/update scores
- Issue operations: create, list, solve issues
- Headline operations: CRUD for meeting headlines
- Configuration management with multiple API key sources
- httpx-based HTTP client with bearer token authentication

[Unreleased]: https://github.com/franccesco/bloomy-python/compare/v0.19.0...HEAD
[0.19.0]: https://github.com/franccesco/bloomy-python/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/franccesco/bloomy-python/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/franccesco/bloomy-python/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/franccesco/bloomy-python/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/franccesco/bloomy-python/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/franccesco/bloomy-python/compare/v0.13.2...v0.14.0
[0.13.2]: https://github.com/franccesco/bloomy-python/compare/v0.13.1...v0.13.2
[0.13.1]: https://github.com/franccesco/bloomy-python/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/franccesco/bloomy-python/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/franccesco/bloomy-python/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/franccesco/bloomy-python/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/franccesco/bloomy-python/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/franccesco/bloomy-python/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/franccesco/bloomy-python/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/franccesco/bloomy-python/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/franccesco/bloomy-python/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/franccesco/bloomy-python/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/franccesco/bloomy-python/compare/v0.1.0...v0.4.0
[0.1.0]: https://github.com/franccesco/bloomy-python/releases/tag/v0.1.0
