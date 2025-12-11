"""Tests for the Users operations."""

from typing import Any
from unittest.mock import Mock

from bloomy.operations.users import UserOperations


class TestUserOperations:
    """Test cases for UserOperations class."""

    def test_details_basic(
        self,
        mock_http_client: Mock,
        sample_user_data: dict[str, Any],
        mock_user_id: Mock,
    ) -> None:
        """Test getting basic user details."""
        mock_response = Mock()
        mock_response.json.return_value = sample_user_data
        mock_http_client.get.return_value = mock_response

        user_ops = UserOperations(mock_http_client)

        result = user_ops.details()

        assert result.id == 123
        assert result.name == "John Doe"
        assert result.image_url == "https://example.com/avatar.jpg"
        assert result.direct_reports is None
        assert result.positions is None

        mock_http_client.get.assert_called_once_with("users/123")

    def test_details_with_direct_reports(
        self,
        mock_http_client: Mock,
        sample_user_data: dict[str, Any],
        mock_user_id: Mock,
    ) -> None:
        """Test getting user details with direct reports."""
        # Mock user details response
        user_response = Mock()
        user_response.json.return_value = sample_user_data

        # Mock direct reports response
        reports_response = Mock()
        reports_response.json.return_value = [
            {
                "Id": 456,
                "Name": "Jane Smith",
                "ImageUrl": "https://example.com/jane.jpg",
            }
        ]

        mock_http_client.get.side_effect = [user_response, reports_response]

        user_ops = UserOperations(mock_http_client)

        result = user_ops.details(include_direct_reports=True)

        assert result.direct_reports is not None
        assert len(result.direct_reports) == 1
        assert result.direct_reports[0].id == 456

    def test_details_with_all(
        self, mock_http_client: Mock, sample_user_data: dict[str, Any]
    ) -> None:
        """Test getting user details with all information."""
        # Mock responses
        user_response = Mock()
        user_response.json.return_value = sample_user_data

        reports_response = Mock()
        reports_response.json.return_value = []

        positions_response = Mock()
        positions_response.json.return_value = [
            {"Group": {"Position": {"Id": 789, "Name": "Manager"}}}
        ]

        mock_http_client.get.side_effect = [
            user_response,
            reports_response,
            positions_response,
        ]

        user_ops = UserOperations(mock_http_client)
        result = user_ops.details(user_id=123, all=True)

        assert result.direct_reports is not None
        assert result.positions is not None
        assert len(result.positions) == 1
        assert result.positions[0].name == "Manager"

    def test_direct_reports(self, mock_http_client: Mock) -> None:
        """Test getting direct reports."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 456,
                "Name": "Jane Smith",
                "ImageUrl": "https://example.com/jane.jpg",
            },
            {
                "Id": 789,
                "Name": "Bob Johnson",
                "ImageUrl": "https://example.com/bob.jpg",
            },
        ]
        mock_http_client.get.return_value = mock_response

        user_ops = UserOperations(mock_http_client)
        result = user_ops.direct_reports(user_id=123)

        assert len(result) == 2
        assert result[0].id == 456
        assert result[0].name == "Jane Smith"
        assert result[1].id == 789

        mock_http_client.get.assert_called_once_with("users/123/directreports")

    def test_positions(self, mock_http_client: Mock) -> None:
        """Test getting user positions."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"Group": {"Position": {"Id": 101, "Name": "Manager"}}},
            {"Group": {"Position": {"Id": 102, "Name": "Team Lead"}}},
        ]
        mock_http_client.get.return_value = mock_response

        user_ops = UserOperations(mock_http_client)
        result = user_ops.positions(user_id=123)

        assert len(result) == 2
        assert result[0].id == 101
        assert result[0].name == "Manager"
        assert result[1].name == "Team Lead"

        mock_http_client.get.assert_called_once_with("users/123/seats")

    def test_search(self, mock_http_client: Mock) -> None:
        """Test searching users."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 123,
                "Name": "John Doe",
                "Description": "Manager",
                "Email": "john@example.com",
                "OrganizationId": 1,
                "ImageUrl": "https://example.com/john.jpg",
            }
        ]
        mock_http_client.get.return_value = mock_response

        user_ops = UserOperations(mock_http_client)
        result = user_ops.search("john")

        assert len(result) == 1
        assert result[0].id == 123
        assert result[0].name == "John Doe"
        assert result[0].email == "john@example.com"

        mock_http_client.get.assert_called_once_with(
            "search/user", params={"term": "john"}
        )

    def test_all_users(self, mock_http_client: Mock) -> None:
        """Test getting all users."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 123,
                "Name": "John Doe",
                "Email": "john@example.com",
                "Description": "Manager",
                "ImageUrl": "https://example.com/john.jpg",
                "ResultType": "User",
            },
            {
                "Id": 456,
                "Name": "Placeholder",
                "Email": "",
                "Description": "",
                "ImageUrl": "/i/userplaceholder",
                "ResultType": "User",
            },
            {"Id": 789, "Name": "Group", "ResultType": "Group"},
        ]
        mock_http_client.get.return_value = mock_response

        user_ops = UserOperations(mock_http_client)
        result = user_ops.all()

        # Should only return non-placeholder users
        assert len(result) == 1
        assert result[0].id == 123

        # Test with placeholders included
        result_with_placeholders = user_ops.all(include_placeholders=True)
        assert len(result_with_placeholders) == 2

        mock_http_client.get.assert_called_with("search/all", params={"term": "%"})
