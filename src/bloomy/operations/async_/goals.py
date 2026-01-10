"""Async goal operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from ...models import (
    ArchivedGoalInfo,
    BulkCreateResult,
    CreatedGoalInfo,
    GoalInfo,
    GoalListResponse,
    GoalStatus,
)
from ...utils.async_base_operations import AsyncBaseOperations
from ..mixins.goals_transform import GoalOperationsMixin

if TYPE_CHECKING:
    from typing import Any


class AsyncGoalOperations(AsyncBaseOperations, GoalOperationsMixin):
    """Async class to handle all operations related to goals (aka "rocks")."""

    async def list(
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

        """
        if user_id is None:
            user_id = await self.get_user_id()

        response = await self._client.get(
            f"rocks/user/{user_id}", params={"include_origin": True}
        )
        response.raise_for_status()
        data = response.json()

        active_goals = self._transform_goal_list(data)

        if archived:
            archived_goals = await self._get_archived_goals(user_id)
            return GoalListResponse(active=active_goals, archived=archived_goals)

        return active_goals

    async def create(
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

        """
        if user_id is None:
            user_id = await self.get_user_id()

        payload = {"title": title, "accountableUserId": user_id}
        response = await self._client.post(f"L10/{meeting_id}/rocks", json=payload)
        response.raise_for_status()
        data = response.json()

        return self._transform_created_goal(data, title, meeting_id, user_id)

    async def delete(self, goal_id: int) -> None:
        """Delete a goal.

        Args:
            goal_id: The ID of the goal to delete

        """
        response = await self._client.delete(f"rocks/{goal_id}")
        response.raise_for_status()

    async def update(
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

        """
        if accountable_user is None:
            accountable_user = await self.get_user_id()

        payload = self._build_goal_update_payload(accountable_user, title, status)

        response = await self._client.put(f"rocks/{goal_id}", json=payload)
        response.raise_for_status()

    async def archive(self, goal_id: int) -> None:
        """Archive a rock with the specified goal ID.

        Args:
            goal_id: The ID of the goal/rock to archive

        """
        response = await self._client.put(f"rocks/{goal_id}/archive")
        response.raise_for_status()

    async def restore(self, goal_id: int) -> None:
        """Restore a previously archived goal identified by the provided goal ID.

        Args:
            goal_id: The unique identifier of the goal to restore

        """
        response = await self._client.put(f"rocks/{goal_id}/restore")
        response.raise_for_status()

    async def _get_archived_goals(
        self, user_id: int | None = None
    ) -> list[ArchivedGoalInfo]:
        """Retrieve all archived goals for a specific user (private method).

        Args:
            user_id: The ID of the user (default is the initialized user ID)

        Returns:
            A list of ArchivedGoalInfo model instances containing archived goal details

        """
        if user_id is None:
            user_id = await self.get_user_id()

        response = await self._client.get(f"archivedrocks/user/{user_id}")
        response.raise_for_status()
        data = response.json()

        return self._transform_archived_goals(data)

    async def create_many(
        self, goals: builtins.list[dict[str, Any]], max_concurrent: int = 5
    ) -> BulkCreateResult[CreatedGoalInfo]:
        """Create multiple goals concurrently in a best-effort manner.

        Processes goals concurrently with a configurable limit to avoid rate limiting.
        Failed operations are captured and returned alongside successful ones.

        Args:
            goals: List of dictionaries containing goal data. Each dict should have:
                - title (required): Title of the goal
                - meeting_id (required): ID of the associated meeting
                - user_id (optional): ID of the responsible user (defaults to
                    current user)
            max_concurrent: Maximum number of concurrent API requests (default: 5)

        Returns:
            BulkCreateResult containing:
                - successful: List of CreatedGoalInfo instances for successful creations
                - failed: List of BulkCreateError instances for failed creations


        Example:
            ```python
            result = await client.goal.create_many([
                {"title": "Q1 Revenue Target", "meeting_id": 123},
                {"title": "Product Launch", "meeting_id": 123, "user_id": 456}
            ])

            print(f"Created {len(result.successful)} goals")
            for error in result.failed:
                print(f"Failed at index {error.index}: {error.error}")
            ```

        """

        async def _create_single(data: dict[str, Any]) -> CreatedGoalInfo:
            return await self.create(
                title=data["title"],
                meeting_id=data["meeting_id"],
                user_id=data.get("user_id"),
            )

        return await self._process_bulk_async(
            goals,
            _create_single,
            required_fields=["title", "meeting_id"],
            max_concurrent=max_concurrent,
        )
