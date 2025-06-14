"""Pytest configuration and fixtures."""

from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, PropertyMock, patch

import httpx
import pytest

from bloomy import Client, Configuration


@pytest.fixture
def mock_response() -> Mock:
    """Create a mock response object."""
    response = Mock(spec=httpx.Response)
    response.is_success = True
    response.status_code = 200
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def mock_http_client(mock_response: Mock) -> Mock:
    """Create a mock HTTP client."""
    client = Mock(spec=httpx.Client)
    client.get = Mock(return_value=mock_response)
    client.post = Mock(return_value=mock_response)
    client.put = Mock(return_value=mock_response)
    client.delete = Mock(return_value=mock_response)
    client.close = Mock()
    return client


@pytest.fixture
def client_with_mock_http(mock_http_client: Mock) -> Any:
    """Create a Bloomy client with mocked HTTP client."""
    with patch("bloomy.client.httpx.Client") as mock_client_class:
        mock_client_class.return_value = mock_http_client
        client = Client(api_key="test-api-key")
        yield client


@pytest.fixture
def mock_config() -> Mock:
    """Create a mock configuration."""
    config = Mock(spec=Configuration)
    config.api_key = "test-api-key"
    return config


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {"Id": 123, "Name": "John Doe", "ImageUrl": "https://example.com/avatar.jpg"}


@pytest.fixture
def sample_meeting_data() -> dict[str, Any]:
    """Sample meeting data for testing."""
    return {"Id": 456, "Name": "Weekly Team Meeting"}


@pytest.fixture
def sample_todo_data() -> dict[str, Any]:
    """Sample todo data for testing."""
    return {
        "Id": 789,
        "Name": "Complete project proposal",
        "DueDate": "2024-12-31",
        "DetailsUrl": "https://example.com/todo/789",
        "Complete": False,
        "CreateTime": "2024-01-01T10:00:00Z",
        "CompleteTime": None,
        "Owner": {"Id": 123, "Name": "John Doe"},
    }


@pytest.fixture
def sample_goal_data() -> dict[str, Any]:
    """Sample goal data for testing."""
    return {
        "Id": 101,
        "Name": "Increase sales by 20%",
        "CreateTime": "2024-01-01T10:00:00Z",
        "DueDate": "2024-12-31",
        "Complete": False,
        "Owner": {"Id": 123, "Name": "John Doe"},
        "Origins": [{"Id": 456, "Name": "Q1 Planning Meeting"}],
    }


@pytest.fixture
def sample_scorecard_data() -> dict[str, Any]:
    """Sample scorecard data for testing."""
    return {
        "Scores": [
            {
                "Id": 201,
                "MeasurableId": 301,
                "AccountableUserId": 123,
                "MeasurableName": "Sales Revenue",
                "Target": 100000,
                "Measured": 95000,
                "Week": "2024-W25",
                "ForWeek": 25,
                "DateEntered": "2024-06-20T10:00:00Z",
            }
        ]
    }


@pytest.fixture
def sample_issue_data() -> dict[str, Any]:
    """Sample issue data for testing."""
    return {
        "Id": 401,
        "Name": "Server performance issue",
        "DetailsUrl": "https://example.com/issue/401",
        "CreateTime": "2024-06-01T10:00:00Z",
        "CloseTime": None,
        "Complete": False,
        "Owner": {"Id": 123, "Name": "John Doe"},
        "Origin": "Infrastructure Meeting",
        "OriginId": 456,
    }


@pytest.fixture
def sample_headline_data() -> dict[str, Any]:
    """Sample headline data for testing."""
    return {
        "Id": 501,
        "Name": "Product launch successful",
        "DetailsUrl": "https://example.com/headline/501",
        "Notes": "Exceeded targets by 15%",
        "Owner": {"Id": 123, "Name": "John Doe"},
        "Origin": "Product Meeting",
        "OriginId": 456,
        "Archived": False,
        "CreateTime": "2024-06-01T10:00:00Z",
        "CloseTime": None,
    }


@pytest.fixture
def mock_user_id() -> Generator[PropertyMock, None, None]:
    """Mock user_id property for operations classes."""
    with patch(
        "bloomy.utils.base_operations.BaseOperations.user_id", new_callable=PropertyMock
    ) as mock:
        mock.return_value = 123
        yield mock
