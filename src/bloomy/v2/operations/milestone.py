"""Milestone operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import (
    MILESTONE_FIELDS,
    MILESTONES_CONNECTION,
    MUTATION_RESULT_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    TimeInput,
    compact,
    dig_nodes,
    to_timestamp,
)
from ..models import Milestone


class MilestoneOperationsMixin:
    """GraphQL documents, inputs, and parsing shared by milestone operations."""

    _MILESTONE_LIST_QUERY = f"""
    query($goalId: Long!) {{
      goal(id: $goalId) {{
        {MILESTONES_CONNECTION}
      }}
    }}
    """

    _MILESTONE_BY_ID_QUERY = f"""
    query($goalId: Long!, $milestoneId: Long!) {{
      goal(id: $goalId) {{
        milestones(where: {{ id: {{ eq: $milestoneId }} }}) {{
          nodes {{
            {MILESTONE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _MILESTONE_CREATE_MUTATION = """
    mutation($input: MilestoneCreateModelInput!) {
      CreateMilestone(input: $input) {
        id
      }
    }
    """

    _MILESTONE_EDIT_MUTATION = """
    mutation($input: MilestoneEditModelInput!) {
      EditMilestone(input: $input) {
        id
      }
    }
    """

    _MILESTONE_DELETE_MUTATION = f"""
    mutation($milestoneId: Long!) {{
      DeleteMilestone(milestoneId: $milestoneId) {{
        {MUTATION_RESULT_FIELDS}
      }}
    }}
    """

    @staticmethod
    def _milestones_from(data: dict[str, Any]) -> list[Milestone]:
        """Validate the milestones of a `_MILESTONE_LIST_QUERY` response.

        Returns:
            The milestones, ordered by due date (empty for an unknown goal).

        """
        return [
            Milestone.model_validate(node)
            for node in dig_nodes(data, "goal", "milestones")
        ]

    @staticmethod
    def _milestone_create_input(
        *,
        goal_id: int,
        title: str,
        due_date: TimeInput,
        completed: bool,
    ) -> dict[str, Any]:
        """Build the `MilestoneCreateModelInput` fields.

        Returns:
            The input fields.

        """
        return {
            "rockId": goal_id,
            "title": title,
            "dueDate": to_timestamp(due_date),
            "completed": completed,
        }

    @staticmethod
    def _milestone_edit_fields(
        *,
        title: str | None,
        due_date: TimeInput | None,
        completed: bool | None,
    ) -> dict[str, Any]:
        """Build the `MilestoneEditModelInput` fields that were given.

        Returns:
            The non-`None` input fields.

        """
        return compact(
            title=title,
            dueDate=None if due_date is None else to_timestamp(due_date),
            completed=completed,
        )


class MilestoneOperations(GraphQLOperations, MilestoneOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to goal milestones.

    Note:
        The GraphQL API has no root `milestone(id)` query, so a milestone is
        read through its parent goal. `update()` and `complete()` therefore
        take `goal_id`: they check that `milestone_id` belongs to that goal
        before writing anything, then re-read the milestone through it.

    """

    def list(self, goal_id: int) -> builtins.list[Milestone]:
        """List the milestones of a goal.

        Args:
            goal_id: The ID of the goal.

        Returns:
            A list of `Milestone` model instances, ordered by due date.

        Example:
            ```python
            client.v2.milestone.list(5265048)
            # Returns: [Milestone(id=1, title='Draft spec', ...), ...]
            ```

        """
        return self._milestones_from(
            self._execute(self._MILESTONE_LIST_QUERY, {"goalId": goal_id})
        )

    def create(
        self,
        goal_id: int,
        title: str,
        due_date: TimeInput,
        completed: bool = False,
    ) -> Milestone:
        """Create a new milestone on a goal.

        Args:
            goal_id: The ID of the goal (rock) to attach the milestone to.
            title: The title of the milestone.
            due_date: The due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            completed: Whether the milestone starts out completed.

        Returns:
            The newly created `Milestone`.

        Example:
            ```python
            client.v2.milestone.create(5265048, "Draft spec", date(2026, 1, 1))
            # Returns: Milestone(id=1, goal_id=5265048, title='Draft spec', ...)
            ```

        """
        input_ = self._milestone_create_input(
            goal_id=goal_id, title=title, due_date=due_date, completed=completed
        )
        result = self._mutate(
            self._MILESTONE_CREATE_MUTATION,
            {"input": input_},
            root_field="CreateMilestone",
            action="create milestone",
        )
        return self._get(goal_id, result["id"])

    def update(
        self,
        milestone_id: int,
        *,
        goal_id: int,
        title: str | None = None,
        due_date: TimeInput | None = None,
        completed: bool | None = None,
    ) -> Milestone:
        """Update an existing milestone.

        Args:
            milestone_id: The ID of the milestone to update.
            goal_id: The ID of the milestone's parent goal (see the class
                `Note`).
            title: New title for the milestone.
            due_date: New due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            completed: New completed state.

        Returns:
            The updated `Milestone`.

        Raises:
            ValueError: If no update fields are provided.

        Example:
            ```python
            client.v2.milestone.update(1, goal_id=5265048, title="Draft spec v2")
            # Returns: Milestone(id=1, title='Draft spec v2', ...)
            ```

        """
        fields = self._milestone_edit_fields(
            title=title, due_date=due_date, completed=completed
        )
        if not fields:
            raise ValueError("At least one field must be provided for update")
        # Checks that the milestone belongs to `goal_id` before writing.
        self._get(goal_id, milestone_id)
        self._mutate(
            self._MILESTONE_EDIT_MUTATION,
            {"input": {"milestoneId": milestone_id, **fields}},
            root_field="EditMilestone",
            action="update milestone",
        )
        return self._get(goal_id, milestone_id)

    def complete(self, milestone_id: int, *, goal_id: int) -> Milestone:
        """Mark a milestone as completed.

        Args:
            milestone_id: The ID of the milestone to complete.
            goal_id: The ID of the milestone's parent goal (see the class
                `Note`).

        Returns:
            The updated `Milestone`.

        """
        return self.update(milestone_id, goal_id=goal_id, completed=True)

    def delete(self, milestone_id: int) -> None:
        """Delete (soft-delete) a milestone.

        Args:
            milestone_id: The ID of the milestone to delete.

        Example:
            ```python
            client.v2.milestone.delete(1)
            ```

        """
        self._mutate(
            self._MILESTONE_DELETE_MUTATION,
            {"milestoneId": milestone_id},
            root_field="DeleteMilestone",
            action="delete milestone",
        )

    def _get(self, goal_id: int, milestone_id: int) -> Milestone:
        """Read a single milestone through its parent goal.

        Returns:
            The `Milestone` model instance. `_one` raises `GraphQLError` if
            the goal has no such milestone.

        """
        data = self._execute(
            self._MILESTONE_BY_ID_QUERY,
            {"goalId": goal_id, "milestoneId": milestone_id},
        )
        return Milestone.model_validate(
            self._one(
                data, "goal", "milestones", label="Milestone", entity_id=milestone_id
            )
        )


class AsyncMilestoneOperations(AsyncGraphQLOperations, MilestoneOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to goal milestones.

    Note:
        See `MilestoneOperations` for why `update()` and `complete()` require
        `goal_id`.

    """

    async def list(self, goal_id: int) -> builtins.list[Milestone]:
        """List the milestones of a goal.

        Args:
            goal_id: The ID of the goal.

        Returns:
            A list of `Milestone` model instances, ordered by due date.

        """
        return self._milestones_from(
            await self._execute(self._MILESTONE_LIST_QUERY, {"goalId": goal_id})
        )

    async def create(
        self,
        goal_id: int,
        title: str,
        due_date: TimeInput,
        completed: bool = False,
    ) -> Milestone:
        """Create a new milestone on a goal.

        Args:
            goal_id: The ID of the goal (rock) to attach the milestone to.
            title: The title of the milestone.
            due_date: The due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            completed: Whether the milestone starts out completed.

        Returns:
            The newly created `Milestone`.

        """
        input_ = self._milestone_create_input(
            goal_id=goal_id, title=title, due_date=due_date, completed=completed
        )
        result = await self._mutate(
            self._MILESTONE_CREATE_MUTATION,
            {"input": input_},
            root_field="CreateMilestone",
            action="create milestone",
        )
        return await self._get(goal_id, result["id"])

    async def update(
        self,
        milestone_id: int,
        *,
        goal_id: int,
        title: str | None = None,
        due_date: TimeInput | None = None,
        completed: bool | None = None,
    ) -> Milestone:
        """Update an existing milestone.

        Args:
            milestone_id: The ID of the milestone to update.
            goal_id: The ID of the milestone's parent goal (see the class
                `Note`).
            title: New title for the milestone.
            due_date: New due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            completed: New completed state.

        Returns:
            The updated `Milestone`.

        Raises:
            ValueError: If no update fields are provided.

        """
        fields = self._milestone_edit_fields(
            title=title, due_date=due_date, completed=completed
        )
        if not fields:
            raise ValueError("At least one field must be provided for update")
        # Checks that the milestone belongs to `goal_id` before writing.
        await self._get(goal_id, milestone_id)
        await self._mutate(
            self._MILESTONE_EDIT_MUTATION,
            {"input": {"milestoneId": milestone_id, **fields}},
            root_field="EditMilestone",
            action="update milestone",
        )
        return await self._get(goal_id, milestone_id)

    async def complete(self, milestone_id: int, *, goal_id: int) -> Milestone:
        """Mark a milestone as completed.

        Args:
            milestone_id: The ID of the milestone to complete.
            goal_id: The ID of the milestone's parent goal (see the class
                `Note`).

        Returns:
            The updated `Milestone`.

        """
        return await self.update(milestone_id, goal_id=goal_id, completed=True)

    async def delete(self, milestone_id: int) -> None:
        """Delete (soft-delete) a milestone.

        Args:
            milestone_id: The ID of the milestone to delete.

        """
        await self._mutate(
            self._MILESTONE_DELETE_MUTATION,
            {"milestoneId": milestone_id},
            root_field="DeleteMilestone",
            action="delete milestone",
        )

    async def _get(self, goal_id: int, milestone_id: int) -> Milestone:
        """Read a single milestone through its parent goal.

        Returns:
            The `Milestone` model instance. `_one` raises `GraphQLError` if
            the goal has no such milestone.

        """
        data = await self._execute(
            self._MILESTONE_BY_ID_QUERY,
            {"goalId": goal_id, "milestoneId": milestone_id},
        )
        return Milestone.model_validate(
            self._one(
                data, "goal", "milestones", label="Milestone", entity_id=milestone_id
            )
        )
