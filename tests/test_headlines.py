"""Tests for the Headlines operations."""

from unittest.mock import Mock

import pytest

from bloomy.operations.headlines import HeadlineOperations


class TestHeadlineOperations:
    """Test cases for HeadlineOperations class."""

    def test_create(self, mock_http_client):
        """Test creating a headline."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 501,
            "Name": "Product launch successful",
            "OwnerId": 789,
            "DetailsUrl": "https://example.com/headline/501",
        }
        mock_http_client.post.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        headline_ops._user_id = 123

        result = headline_ops.create(
            meeting_id=456,
            title="Product launch successful",
            owner_id=789,
            notes="Exceeded targets by 15%",
        )

        assert result.id == 501
        assert result.title == "Product launch successful"
        assert result.owner_details.id == 789
        assert result.notes_url == "https://example.com/headline/501"

        mock_http_client.post.assert_called_once_with(
            "L10/456/headlines",
            json={
                "title": "Product launch successful",
                "ownerId": 789,
                "notes": "Exceeded targets by 15%",
            },
        )

    def test_create_default_owner(self, mock_http_client):
        """Test creating a headline with default owner."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Id": 501,
            "Name": "Product launch successful",
            "OwnerId": 123,
            "DetailsUrl": "https://example.com/headline/501",
        }
        mock_http_client.post.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        headline_ops._user_id = 123

        result = headline_ops.create(meeting_id=456, title="Product launch successful")

        assert result.owner_details.id == 123

        mock_http_client.post.assert_called_once_with(
            "L10/456/headlines",
            json={"title": "Product launch successful", "ownerId": 123},
        )

    def test_update(self, mock_http_client):
        """Test updating a headline."""
        mock_response = Mock()
        mock_response.json.return_value = {"Id": 501, "Name": "Updated headline"}
        mock_http_client.put.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        result = headline_ops.update(headline_id=501, title="Updated headline")

        assert result is True

        mock_http_client.put.assert_called_once_with(
            "headline/501", json={"title": "Updated headline"}
        )

    def test_details(self, mock_http_client, sample_headline_data):
        """Test getting headline details."""
        mock_response = Mock()
        mock_response.json.return_value = sample_headline_data
        mock_http_client.get.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        result = headline_ops.details(headline_id=501)

        assert result.id == 501
        assert result.title == "Product launch successful"
        assert result.notes_url == "https://example.com/headline/501"
        assert result.owner_details.id == 123
        assert result.meeting_details.title == "Product Meeting"

        mock_http_client.get.assert_called_once_with(
            "headline/501", params={"Include_Origin": "true"}
        )

    def test_list_meeting_headlines(self, mock_http_client):
        """Test listing headlines for a meeting."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 501,
                "Name": "Product launch successful",
                "CreateTime": "2024-06-01T10:00:00Z",
                "OriginId": 456,
                "Origin": "Product Meeting",
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Archived": False,
                "CloseTime": None,
            }
        ]
        mock_http_client.get.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        result = headline_ops.list(meeting_id=456)

        assert len(result) == 1
        assert result[0].id == 501
        assert result[0].title == "Product launch successful"

        mock_http_client.get.assert_called_once_with("l10/456/headlines")

    def test_list_user_headlines(self, mock_http_client):
        """Test listing headlines for a user."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "Id": 501,
                "Name": "Product launch successful",
                "CreateTime": "2024-06-01T10:00:00Z",
                "OriginId": 456,
                "Origin": "Product Meeting",
                "Owner": {"Id": 123, "Name": "John Doe"},
                "Archived": False,
                "CloseTime": None,
            }
        ]
        mock_http_client.get.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        headline_ops._user_id = 123

        result = headline_ops.list()

        assert len(result) == 1
        mock_http_client.get.assert_called_once_with("headline/users/123")

    def test_list_both_params_error(self, mock_http_client):
        """Test error when both user_id and meeting_id are provided."""
        headline_ops = HeadlineOperations(mock_http_client)

        with pytest.raises(ValueError) as exc_info:
            headline_ops.list(user_id=123, meeting_id=456)

        assert "Please provide either" in str(exc_info.value)

    def test_delete(self, mock_http_client):
        """Test deleting a headline."""
        mock_response = Mock()
        mock_http_client.delete.return_value = mock_response

        headline_ops = HeadlineOperations(mock_http_client)
        result = headline_ops.delete(headline_id=501)

        assert result is True
        mock_http_client.delete.assert_called_once_with("headline/501")
