"""Mixin for shared goal operations logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models import (
    ArchivedGoalInfo,
    CreatedGoalInfo,
    GoalInfo,
    GoalStatus,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class GoalOperationsMixin:
    """Shared logic for goal operations."""

    def _transform_goal_list(self, data: Sequence[dict[str, Any]]) -> list[GoalInfo]:
        """Transform API response to list of GoalInfo models.

        Args:
            data: The raw API response data.

        Returns:
            A list of GoalInfo models.

        """
        return [
            GoalInfo(
                id=goal["Id"],
                user_id=goal["Owner"]["Id"],
                user_name=goal["Owner"]["Name"],
                title=goal["Name"],
                created_at=goal["CreateTime"],
                due_date=goal["DueDate"],
                status="Completed" if goal.get("Complete") else "Incomplete",
                meeting_id=goal["Origins"][0]["Id"] if goal.get("Origins") else None,
                meeting_title=(
                    goal["Origins"][0]["Name"] if goal.get("Origins") else None
                ),
            )
            for goal in data
        ]

    def _transform_archived_goals(
        self, data: Sequence[dict[str, Any]]
    ) -> list[ArchivedGoalInfo]:
        """Transform API response to list of ArchivedGoalInfo models.

        Args:
            data: The raw API response data.

        Returns:
            A list of ArchivedGoalInfo models.

        """
        return [
            ArchivedGoalInfo(
                id=goal["Id"],
                title=goal["Name"],
                created_at=goal["CreateTime"],
                due_date=goal["DueDate"],
                status="Complete" if goal.get("Complete") else "Incomplete",
            )
            for goal in data
        ]

    def _transform_created_goal(
        self, data: dict[str, Any], title: str, meeting_id: int, user_id: int
    ) -> CreatedGoalInfo:
        """Transform API response to CreatedGoalInfo model.

        Args:
            data: The raw API response data.
            title: The title of the goal.
            meeting_id: The ID of the meeting associated with the goal.
            user_id: The ID of the user responsible for the goal.

        Returns:
            A CreatedGoalInfo model.

        """
        # Map completion status
        completion_map = {2: "complete", 1: "on", 0: "off"}
        status = completion_map.get(data.get("Completion", 0), "off")

        return CreatedGoalInfo(
            id=data["Id"],
            user_id=user_id,
            user_name=data["Owner"]["Name"],
            title=title,
            meeting_id=meeting_id,
            meeting_title=data["Origins"][0]["Name"],
            status=status,
            created_at=data["CreateTime"],
        )

    def _build_goal_update_payload(
        self,
        accountable_user: int,
        title: str | None = None,
        status: GoalStatus | str | None = None,
    ) -> dict[str, Any]:
        """Build payload for goal update operation.

        Args:
            accountable_user: The ID of the user responsible for the goal.
            title: The new title of the goal.
            status: The status value (GoalStatus enum or string).

        Returns:
            A dictionary containing the update payload.

        Raises:
            ValueError: If an invalid status value is provided.

        """
        payload: dict[str, Any] = {"accountableUserId": accountable_user}

        if title is not None:
            payload["title"] = title

        if status is not None:
            valid_status = {"on": "OnTrack", "off": "AtRisk", "complete": "Complete"}
            # Handle both GoalStatus enum and string
            status_value = status.value if isinstance(status, GoalStatus) else status
            status_key = status_value.lower()
            if status_key not in valid_status:
                raise ValueError(
                    "Invalid status value. Must be 'on', 'off', or 'complete'."
                )
            payload["completion"] = valid_status[status_key]

        return payload
