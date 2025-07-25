"""Goal operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from ..models import (
    ArchivedGoalInfo,
    BulkCreateError,
    BulkCreateResult,
    CreatedGoalInfo,
    GoalInfo,
    GoalListResponse,
)
from ..utils.base_operations import BaseOperations

if TYPE_CHECKING:
    from typing import Any


class GoalOperations(BaseOperations):
    """Class to handle all the operations related to goals (also known as "rocks").

    Note:
        This class is already initialized via the client and usable as
        `client.goal.method`

    """

    def list(
        self, user_id: int | None = None, archived: bool = False
    ) -> builtins.list[GoalInfo] | GoalListResponse:
        """List all goals for a specific user.

        Args:
            user_id: The ID of the user (default is the initialized user ID)
            archived: Whether to include archived goals (default: False)

        Returns:
            Either:
            - A list of GoalInfo model instances if archived is false
            - A GoalListResponse model with 'active' and 'archived' lists of
                GoalInfo instances if archived is true

        Examples:
            List active goals:
            ```python
            client.goal.list()
            # Returns: [GoalInfo(id=1, title='Complete project', ...)]
            ```

            List both active and archived goals:
            ```python
            client.goal.list(archived=True)
            # Returns: GoalListResponse(
            #     active=[GoalInfo(id=1, ...)],
            #     archived=[ArchivedGoalInfo(id=2, ...)]
            # )
            ```

        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(
            f"rocks/user/{user_id}", params={"include_origin": True}
        )
        response.raise_for_status()
        data = response.json()

        active_goals: list[GoalInfo] = [
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

        if archived:
            archived_goals = self._get_archived_goals(user_id)
            return GoalListResponse(active=active_goals, archived=archived_goals)

        return active_goals

    def create(
        self, title: str, meeting_id: int, user_id: int | None = None
    ) -> CreatedGoalInfo:
        """Create a new goal.

        Args:
            title: The title of the new goal
            meeting_id: The ID of the meeting associated with the goal
            user_id: The ID of the user responsible for the goal (default:
                initialized user ID)

        Returns:
            A CreatedGoalInfo model instance representing the newly created goal

        Example:
            ```python
            client.goal.create(title="New Goal", meeting_id=1)
            # Returns: CreatedGoalInfo(id=1, title='New Goal', meeting_id=1, ...)
            ```

        """
        if user_id is None:
            user_id = self.user_id

        payload = {"title": title, "accountableUserId": user_id}
        response = self._client.post(f"L10/{meeting_id}/rocks", json=payload)
        response.raise_for_status()
        data = response.json()

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

    def delete(self, goal_id: int) -> bool:
        """Delete a goal.

        Args:
            goal_id: The ID of the goal to delete

        Returns:
            True if deletion was successful

        Example:
            ```python
            client.goal.delete(1)
            # Returns: True
            ```

        """
        response = self._client.delete(f"rocks/{goal_id}")
        response.raise_for_status()
        return True

    def update(
        self,
        goal_id: int,
        title: str | None = None,
        accountable_user: int | None = None,
        status: str | None = None,
    ) -> bool:
        """Update a goal.

        Args:
            goal_id: The ID of the goal to update
            title: The new title of the goal
            accountable_user: The ID of the user responsible for the goal
                (default: initialized user ID)
            status: The status value ('on', 'off', or 'complete')

        Returns:
            True if the update was successful

        Raises:
            ValueError: If an invalid status value is provided

        Example:
            ```python
            client.goal.update(goal_id=1, title="Updated Goal", status='on')
            # Returns: True
            ```

        """
        if accountable_user is None:
            accountable_user = self.user_id

        payload: dict[str, Any] = {"accountableUserId": accountable_user}

        if title is not None:
            payload["title"] = title

        if status is not None:
            valid_status = {"on": "OnTrack", "off": "AtRisk", "complete": "Complete"}
            status_key = status.lower()
            if status_key not in valid_status:
                raise ValueError(
                    "Invalid status value. Must be 'on', 'off', or 'complete'."
                )
            payload["completion"] = valid_status[status_key]

        response = self._client.put(f"rocks/{goal_id}", json=payload)
        response.raise_for_status()
        return True

    def archive(self, goal_id: int) -> bool:
        """Archive a rock with the specified goal ID.

        Args:
            goal_id: The ID of the goal/rock to archive

        Returns:
            True if the archival was successful, False otherwise

        Example:
            ```python
            goals.archive(123)
            # Returns: True
            ```

        """
        response = self._client.put(f"rocks/{goal_id}/archive")
        response.raise_for_status()
        return True

    def restore(self, goal_id: int) -> bool:
        """Restore a previously archived goal identified by the provided goal ID.

        Args:
            goal_id: The unique identifier of the goal to restore

        Returns:
            True if the restore operation was successful, False otherwise

        Example:
            ```python
            goals.restore(123)
            # Returns: True
            ```

        """
        response = self._client.put(f"rocks/{goal_id}/restore")
        response.raise_for_status()
        return True

    def _get_archived_goals(self, user_id: int | None = None) -> list[ArchivedGoalInfo]:
        """Retrieve all archived goals for a specific user (private method).

        Args:
            user_id: The ID of the user (default is the initialized user ID)

        Returns:
            A list of ArchivedGoalInfo model instances containing archived goal details

        Example:
            ```python
            goal._get_archived_goals()
            # Returns: [ArchivedGoalInfo(id=1, title='Archived Goal',
            #                           created_at='2024-06-10', ...), ...]
            ```

        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(f"archivedrocks/user/{user_id}")
        response.raise_for_status()
        data = response.json()

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

    def create_many(
        self, goals: builtins.list[dict[str, Any]]
    ) -> BulkCreateResult[CreatedGoalInfo]:
        """Create multiple goals in a best-effort manner.

        Processes each goal sequentially to avoid rate limiting.
        Failed operations are captured and returned alongside successful ones.

        Args:
            goals: List of dictionaries containing goal data. Each dict should have:
                - title (required): Title of the goal
                - meeting_id (required): ID of the associated meeting
                - user_id (optional): ID of the responsible user (defaults to
                    current user)

        Returns:
            BulkCreateResult containing:
                - successful: List of CreatedGoalInfo instances for successful creations
                - failed: List of BulkCreateError instances for failed creations

        Raises:
            ValueError: When required parameters are missing in goal data

        Example:
            ```python
            result = client.goal.create_many([
                {"title": "Q1 Revenue Target", "meeting_id": 123},
                {"title": "Product Launch", "meeting_id": 123, "user_id": 456}
            ])

            print(f"Created {len(result.successful)} goals")
            for error in result.failed:
                print(f"Failed at index {error.index}: {error.error}")
            ```

        """
        successful: builtins.list[CreatedGoalInfo] = []
        failed: builtins.list[BulkCreateError] = []

        for index, goal_data in enumerate(goals):
            try:
                # Extract parameters from the goal data
                title = goal_data.get("title")
                meeting_id = goal_data.get("meeting_id")
                user_id = goal_data.get("user_id")

                # Validate required parameters
                if title is None:
                    raise ValueError("title is required")
                if meeting_id is None:
                    raise ValueError("meeting_id is required")

                # Create the goal
                created_goal = self.create(
                    title=title, meeting_id=meeting_id, user_id=user_id
                )
                successful.append(created_goal)

            except Exception as e:
                failed.append(
                    BulkCreateError(index=index, input_data=goal_data, error=str(e))
                )

        return BulkCreateResult(successful=successful, failed=failed)
