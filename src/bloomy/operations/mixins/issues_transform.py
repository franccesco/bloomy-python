"""Mixin for shared issue operations logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models import (
    CreatedIssue,
    IssueDetails,
    IssueListItem,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class IssueOperationsMixin:
    """Shared logic for issue operations."""

    def _transform_issue_details(self, data: dict[str, Any]) -> IssueDetails:
        """Transform API response to IssueDetails model.

        Args:
            data: The raw API response data.

        Returns:
            An IssueDetails model.

        """
        return IssueDetails(
            id=data["Id"],
            title=data["Name"],
            notes_url=data["DetailsUrl"],
            created_at=data["CreateTime"],
            completed_at=data["CloseTime"],
            meeting_id=data["OriginId"],
            meeting_title=data["Origin"],
            user_id=data["Owner"]["Id"],
            user_name=data["Owner"]["Name"],
        )

    def _transform_issue_list(
        self, data: Sequence[dict[str, Any]]
    ) -> list[IssueListItem]:
        """Transform API response to list of IssueListItem models.

        Args:
            data: The raw API response data.

        Returns:
            A list of IssueListItem models.

        """
        return [
            IssueListItem(
                id=issue["Id"],
                title=issue["Name"],
                notes_url=issue["DetailsUrl"],
                created_at=issue["CreateTime"],
                meeting_id=issue["OriginId"],
                meeting_title=issue["Origin"],
            )
            for issue in data
        ]

    def _transform_created_issue(self, data: dict[str, Any]) -> CreatedIssue:
        """Transform API response to CreatedIssue model.

        Args:
            data: The raw API response data.

        Returns:
            A CreatedIssue model.

        """
        return CreatedIssue(
            id=data["Id"],
            meeting_id=data["OriginId"],
            meeting_title=data["Origin"],
            title=data["Name"],
            user_id=data["Owner"]["Id"],
            notes_url=data["DetailsUrl"],
        )
