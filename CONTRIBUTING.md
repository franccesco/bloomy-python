# Contributing to Bloomy

Thank you for your interest in contributing to Bloomy! This document outlines the guidelines for contributing to the project.

## Did you find a bug?

- Before creating an issue, please ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/franccesco/bloomy/issues)
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/franccesco/bloomy/issues/new). Be sure to include a title and clear description, as much relevant information as possible. A code sample or a screenshot would be helpful.
- You can also write issues if you want to discuss a feature request or a general question about the project.

## Do you want to contribute to the Bloomy project?

PR's are welcome! Just make sure you have discussed the changes you want to make with the project maintainer before you start working on them. Before getting started, make sure you are not submitting a PR that's purely cosmetic (linting changes, whitespace, etc.)

If you want to contribute to the project, please follow these steps:

### Development Setup

> [!IMPORTANT]
> Make sure you have a Bloom Growth account and that you're using a user that won't disrupt the experience of other users. The tests will create and delete meetings, so make sure you're not using a user that has important meetings scheduled.

1. Fork and clone the repository:

```sh
git clone https://github.com/your-username/bloomy.git
```

2. Install the dependencies:

```sh
uv sync --all-extras
```

3. Set up [pre-commit](https://pre-commit.com) hooks:

```sh
pre-commit install
```

4. Add your Bloom Growth username and password to an `.env` file. I use [direnv](https://direnv.net/) to manage my environment variables.

```sh
export USERNAME=your_username
export PASSWORD=your_password
```

5. Run the tests to make sure everything is green:

```sh
uv run pytest -v --tb=short
```

### Making Changes

Once everything is green, you can start making changes. Make sure to write tests for your changes and run the tests before submitting a PR.

As for coding style guidelines make sure you:

- Follow PEP 8 style guide enforced by [Ruff](https://github.com/astral-sh/ruff)
- Use Python docstrings for classes and methods
- Include type annotations for all public APIs
- Run `uv run ruff format .` before committing
- Run `uv run ruff check . --fix` to auto-fix linting issues
- Run `uv run pyright` for type checking

### Pull Request Process

1. Make sure your PR is up-to-date with the `main` branch.
2. Make sure your PR passes the CI checks.
3. Make sure your PR has a clear title and description.
4. Update the version according to [Semantic Versioning](https://semver.org/).
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for your commit messages.

Make sure to follow these guidelines to ensure your PR is accepted and merged quickly. Rinse and repeat! 🚀

## Comments on Test Structure

When developing new features, make sure to add a test. Tests will usually have the following basic structure:

```python
import pytest
from unittest.mock import Mock
from bloomy import Client

class TestFeature:
    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        client = Mock(spec=Client)
        client._http_client = Mock()
        return client
    
    @pytest.fixture
    def sample_meeting(self):
        """Sample meeting data for tests."""
        return {
            "Id": 123,
            "Name": "Test Meeting",
            "StartTime": "10:00 AM",
            "EndTime": "11:00 AM"
        }
    
    def test_feature_action(self, mock_client, sample_meeting):
        """Test the expected action."""
        # Set up mock response
        mock_client._http_client.get.return_value.json.return_value = sample_meeting
        
        # Perform the action
        result = mock_client.meeting.details(123)
        
        # Assert the result
        assert result["id"] == 123
        assert result["name"] == "Test Meeting"
```

Tests use pytest fixtures defined in `conftest.py` for common test data and mock objects. All API responses should be mocked to avoid making real API calls during tests.
