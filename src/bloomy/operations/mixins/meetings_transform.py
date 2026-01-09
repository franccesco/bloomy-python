"""Mixin for shared meeting operations logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models import (
    Issue,
    MeetingAttendee,
    ScorecardMetric,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class MeetingOperationsMixin:
    """Shared logic for meeting operations."""

    def _transform_attendees(
        self, data: Sequence[dict[str, Any]]
    ) -> list[MeetingAttendee]:
        """Transform API response to list of MeetingAttendee models.

        Args:
            data: The raw API response data.

        Returns:
            A list of MeetingAttendee models.

        """
        return [
            MeetingAttendee(
                UserId=attendee["Id"],
                Name=attendee["Name"],
                ImageUrl=attendee.get("ImageUrl", ""),
            )
            for attendee in data
        ]

    def _transform_metrics(self, raw_data: Any) -> list[ScorecardMetric]:
        """Transform API response to list of ScorecardMetric models.

        Args:
            raw_data: The raw API response data.

        Returns:
            A list of ScorecardMetric models.

        """
        if not isinstance(raw_data, list):
            return []

        metrics: list[ScorecardMetric] = []
        # Type the list explicitly
        data_list: list[Any] = raw_data  # type: ignore[assignment]
        for item in data_list:
            if not isinstance(item, dict):
                continue

            # Cast to Any dict to satisfy type checker
            item_dict: dict[str, Any] = item  # type: ignore[assignment]
            measurable_id = item_dict.get("Id")
            measurable_name = item_dict.get("Name")

            if not measurable_id or not measurable_name:
                continue

            owner_data = item_dict.get("Owner", {})
            if not isinstance(owner_data, dict):
                owner_data = {}
            owner_dict: dict[str, Any] = owner_data  # type: ignore[assignment]

            metrics.append(
                ScorecardMetric(
                    Id=int(measurable_id),
                    Title=str(measurable_name).strip(),
                    Target=float(item_dict.get("Target", 0)),
                    Unit=str(item_dict.get("Modifiers", "")),
                    WeekNumber=0,  # Not provided in this endpoint
                    Value=None,
                    MetricType=str(item_dict.get("Direction", "")),
                    AccountableUserId=int(owner_dict.get("Id") or 0),
                    AccountableUserName=str(owner_dict.get("Name") or ""),
                    IsInverse=False,
                )
            )

        return metrics

    def _transform_meeting_issues(
        self, data: Sequence[dict[str, Any]], meeting_id: int
    ) -> list[Issue]:
        """Transform API response to list of Issue models.

        Args:
            data: The raw API response data.
            meeting_id: The ID of the meeting.

        Returns:
            A list of Issue models.

        """
        return [
            Issue(
                Id=issue["Id"],
                Name=issue["Name"],
                DetailsUrl=issue["DetailsUrl"],
                CreateDate=issue["CreateTime"],
                ClosedDate=issue["CloseTime"],
                CompletionDate=issue.get("CompleteTime"),
                OwnerId=issue.get("Owner", {}).get("Id", 0),
                OwnerName=issue.get("Owner", {}).get("Name", ""),
                OwnerImageUrl=issue.get("Owner", {}).get("ImageUrl", ""),
                MeetingId=meeting_id,
                MeetingName=issue["Origin"],
            )
            for issue in data
        ]
