"""Goal operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from ..models import (
    ArchivedGoalInfo,
    BulkCreateResult,
    CreatedGoalInfo,
    GoalInfo,
    GoalListResponse,
    GoalStatus,
)
from ..utils.base_operations import BaseOperations
from .mixins.goals_transform import GoalOperationsMixin

if TYPE_CHECKING:
    from typing import Any


class GoalOperations(BaseOperations, GoalOperationsMixin):
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

        active_goals = self._transform_goal_list(data)

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

        return self._transform_created_goal(data, title, meeting_id, user_id)

    def delete(self, goal_id: int) -> None:
        """Delete a goal.

        Args:
            goal_id: The ID of the goal to delete

        Example:
            ```python
            client.goal.delete(1)
            ```

        """
        response = self._client.delete(f"rocks/{goal_id}")
        response.raise_for_status()

    def update(
        self,
        goal_id: int,
        title: str | None = None,
        accountable_user: int | None = None,
        status: GoalStatus | str | None = None,
    ) -> None:
        """Update a goal.

        Args:
            goal_id: The ID of the goal to update
            title: The new title of the goal
            accountable_user: The ID of the user responsible for the goal
                (default: initialized user ID)
            status: The status value. Can be a GoalStatus enum member or string
                ('on', 'off', or 'complete'). Use GoalStatus.ON_TRACK,
                GoalStatus.AT_RISK, or GoalStatus.COMPLETE for type safety.
                Invalid values will raise ValueError via the update payload builder.

        Example:
            ```python
            from bloomy import GoalStatus

            # Using enum (recommended)
            client.goal.update(goal_id=1, status=GoalStatus.ON_TRACK)

            # Using string
            client.goal.update(goal_id=1, status='on')
            ```

        """
        if accountable_user is None:
            accountable_user = self.user_id

        payload = self._build_goal_update_payload(accountable_user, title, status)

        response = self._client.put(f"rocks/{goal_id}", json=payload)
        response.raise_for_status()

    def archive(self, goal_id: int) -> None:
        """Archive a rock with the specified goal ID.

        Args:
            goal_id: The ID of the goal/rock to archive

        Example:
            ```python
            client.goal.archive(123)
            ```

        """
        response = self._client.put(f"rocks/{goal_id}/archive")
        response.raise_for_status()

    def restore(self, goal_id: int) -> None:
        """Restore a previously archived goal identified by the provided goal ID.

        Args:
            goal_id: The unique identifier of the goal to restore

        Example:
            ```python
            client.goal.restore(123)
            ```

        """
        response = self._client.put(f"rocks/{goal_id}/restore")
        response.raise_for_status()

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

        return self._transform_archived_goals(data)

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

        def _create_single(data: dict[str, Any]) -> CreatedGoalInfo:
            return self.create(
                title=data["title"],
                meeting_id=data["meeting_id"],
                user_id=data.get("user_id"),
            )

        return self._process_bulk_sync(
            goals, _create_single, required_fields=["title", "meeting_id"]
        )
