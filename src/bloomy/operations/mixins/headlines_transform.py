"""Mixin for shared headline operations logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models import (
    HeadlineDetails,
    HeadlineListItem,
    MeetingInfo,
    OwnerDetails,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class HeadlineOperationsMixin:
    """Shared logic for headline operations."""

    def _transform_headline_details(self, data: dict[str, Any]) -> HeadlineDetails:
        """Transform API response to HeadlineDetails model.

        Args:
            data: The raw API response data.

        Returns:
            A HeadlineDetails model.

        """
        return HeadlineDetails(
            id=data["Id"],
            title=data["Name"],
            notes_url=data["DetailsUrl"],
            meeting_details=MeetingInfo(
                id=data["OriginId"],
                title=data["Origin"],
            ),
            owner_details=OwnerDetails(
                id=data["Owner"]["Id"],
                name=data["Owner"]["Name"],
            ),
            archived=data["Archived"],
            created_at=data["CreateTime"],
            closed_at=data["CloseTime"],
        )

    def _transform_headline_list(
        self, data: Sequence[dict[str, Any]]
    ) -> list[HeadlineListItem]:
        """Transform API response to list of HeadlineListItem models.

        Args:
            data: The raw API response data.

        Returns:
            A list of HeadlineListItem models.

        """
        return [
            HeadlineListItem(
                id=headline["Id"],
                title=headline["Name"],
                meeting_details=MeetingInfo(
                    id=headline["OriginId"],
                    title=headline["Origin"],
                ),
                owner_details=OwnerDetails(
                    id=headline["Owner"]["Id"],
                    name=headline["Owner"]["Name"],
                ),
                archived=headline["Archived"],
                created_at=headline["CreateTime"],
                closed_at=headline["CloseTime"],
            )
            for headline in data
        ]
