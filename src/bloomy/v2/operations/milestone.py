"""Milestone operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from datetime import date, datetime
from typing import Any

from ...exceptions import GraphQLError
from ..base import (
    MUTATION_RESULT_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    dig_nodes,
)
from ..models import Milestone

#: Selected on every milestone read. Kept in sync with `goal.py`'s inline
#: milestone subselection (duplicated rather than imported, to keep the two
#: entity modules independent).
_MILESTONE_FIELDS = "id goalId title dueDate completed status dateCreated"


class MilestoneOperationsMixin:
    """Shared GraphQL documents and response transforms for milestone operations."""

    # There is no root `milestone(id)` query (see module docstring on
    # `MilestoneOperations`), so both the list and the by-id read go through
    # `goal(id){ milestones(...) }`. `dateDeleted` is already filtered
    # server-side (soft-deleted milestones are never returned), but the
    # explicit filter is kept for parity with the web app's own query.
    _MILESTONE_LIST_QUERY = f"""
    query($goalId: Long!) {{
      goal(id: $goalId) {{
        milestones(
          where: {{ and: [{{ dateDeleted: {{ eq: null }} }}] }}
          order: [{{ dueDate: ASC }}]
        ) {{
          nodes {{
            {_MILESTONE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _MILESTONE_BY_ID_QUERY = f"""
    query($goalId: Long!, $milestoneId: Long!) {{
      goal(id: $goalId) {{
        milestones(where: {{ id: {{ eq: $milestoneId }} }}) {{
          nodes {{
            {_MILESTONE_FIELDS}
          }}
        }}
      }}
    }}
    """

    # CreateMilestone/EditMilestone return only `IdModel { id }` (verified
    # live against production), not the `{success message errorDetails}`
    # shape `_run_mutation` expects. A failed create/edit raises through the
    # standard `errors` array instead (an invalid input, e.g. a bad `status`
    # string, throws server-side and surfaces there), so these are executed
    # with plain `_execute`.
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

    # DeleteMilestone genuinely returns `GraphQLResponseBase`
    # (`{success message errorDetails}`), unlike Create/EditMilestone.
    _MILESTONE_DELETE_MUTATION = f"""
    mutation($milestoneId: Long!) {{
      DeleteMilestone(milestoneId: $milestoneId) {{
        {MUTATION_RESULT_FIELDS}
      }}
    }}
    """

    def _transform_milestone(self, data: dict[str, Any]) -> Milestone:
        """Transform a raw GraphQL milestone object into a `Milestone` model.

        Returns:
            A `Milestone` model instance.

        """
        return Milestone(**data)


class MilestoneOperations(GraphQLOperations, MilestoneOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to goal milestones.

    Note:
        The GraphQL API has no root `milestone(id)` query — a milestone can
        only be read through its parent goal (`goal(id){ milestones }`). So
        `update()` and `complete()`, which need to re-read the milestone
        after editing it, require `goal_id` in addition to `milestone_id`.
        `delete()` does not, since `DeleteMilestone` does not return a
        `Milestone`.

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
        data = self._execute(self._MILESTONE_LIST_QUERY, {"goalId": goal_id})
        nodes = dig_nodes(data, "goal", "milestones")
        return [self._transform_milestone(node) for node in nodes]

    def create(
        self,
        goal_id: int,
        title: str,
        due_date: datetime | date | float | int,
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
        input_: dict[str, Any] = {
            "rockId": goal_id,
            "title": title,
            "dueDate": self._to_timestamp(due_date),
            "completed": completed,
        }
        data = self._execute(self._MILESTONE_CREATE_MUTATION, {"input": input_})
        return self._get(goal_id, data["CreateMilestone"]["id"])

    def update(
        self,
        milestone_id: int,
        goal_id: int,
        *,
        title: str | None = None,
        due_date: datetime | date | float | int | None = None,
        completed: bool | None = None,
    ) -> Milestone:
        """Update an existing milestone.

        Args:
            milestone_id: The ID of the milestone to update.
            goal_id: The ID of the milestone's parent goal, needed to re-read
                it afterwards (see the class `Note`).
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
            client.v2.milestone.update(1, 5265048, title="Draft spec v2")
            # Returns: Milestone(id=1, title='Draft spec v2', ...)
            ```

        """
        if title is None and due_date is None and completed is None:
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"milestoneId": milestone_id}
        if title is not None:
            input_["title"] = title
        if due_date is not None:
            input_["dueDate"] = self._to_timestamp(due_date)
        if completed is not None:
            input_["completed"] = completed

        self._execute(self._MILESTONE_EDIT_MUTATION, {"input": input_})
        return self._get(goal_id, milestone_id)

    def complete(self, milestone_id: int, goal_id: int) -> Milestone:
        """Mark a milestone as completed.

        Args:
            milestone_id: The ID of the milestone to complete.
            goal_id: The ID of the milestone's parent goal, needed to re-read
                it afterwards (see the class `Note`).

        Returns:
            The updated `Milestone`.

        """
        self._execute(
            self._MILESTONE_EDIT_MUTATION,
            {"input": {"milestoneId": milestone_id, "completed": True}},
        )
        return self._get(goal_id, milestone_id)

    def delete(self, milestone_id: int) -> None:
        """Delete (soft-delete) a milestone.

        Args:
            milestone_id: The ID of the milestone to delete.

        Example:
            ```python
            client.v2.milestone.delete(1)
            ```

        """
        self._run_mutation(
            self._MILESTONE_DELETE_MUTATION,
            {"milestoneId": milestone_id},
            root_field="DeleteMilestone",
            action="delete milestone",
        )

    def _get(self, goal_id: int, milestone_id: int) -> Milestone:
        """Re-read a single milestone through its parent goal.

        Returns:
            The `Milestone` model instance.

        Raises:
            GraphQLError: If the milestone is not found under the goal.

        """
        data = self._execute(
            self._MILESTONE_BY_ID_QUERY,
            {"goalId": goal_id, "milestoneId": milestone_id},
        )
        nodes = dig_nodes(data, "goal", "milestones")
        if not nodes:
            raise GraphQLError(
                f"milestone {milestone_id} not found under goal {goal_id}"
            )
        return self._transform_milestone(nodes[0])


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
        data = await self._execute(self._MILESTONE_LIST_QUERY, {"goalId": goal_id})
        nodes = dig_nodes(data, "goal", "milestones")
        return [self._transform_milestone(node) for node in nodes]

    async def create(
        self,
        goal_id: int,
        title: str,
        due_date: datetime | date | float | int,
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
        input_: dict[str, Any] = {
            "rockId": goal_id,
            "title": title,
            "dueDate": self._to_timestamp(due_date),
            "completed": completed,
        }
        data = await self._execute(self._MILESTONE_CREATE_MUTATION, {"input": input_})
        return await self._get(goal_id, data["CreateMilestone"]["id"])

    async def update(
        self,
        milestone_id: int,
        goal_id: int,
        *,
        title: str | None = None,
        due_date: datetime | date | float | int | None = None,
        completed: bool | None = None,
    ) -> Milestone:
        """Update an existing milestone.

        Args:
            milestone_id: The ID of the milestone to update.
            goal_id: The ID of the milestone's parent goal, needed to re-read
                it afterwards (see the class `Note`).
            title: New title for the milestone.
            due_date: New due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            completed: New completed state.

        Returns:
            The updated `Milestone`.

        Raises:
            ValueError: If no update fields are provided.

        """
        if title is None and due_date is None and completed is None:
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"milestoneId": milestone_id}
        if title is not None:
            input_["title"] = title
        if due_date is not None:
            input_["dueDate"] = self._to_timestamp(due_date)
        if completed is not None:
            input_["completed"] = completed

        await self._execute(self._MILESTONE_EDIT_MUTATION, {"input": input_})
        return await self._get(goal_id, milestone_id)

    async def complete(self, milestone_id: int, goal_id: int) -> Milestone:
        """Mark a milestone as completed.

        Args:
            milestone_id: The ID of the milestone to complete.
            goal_id: The ID of the milestone's parent goal, needed to re-read
                it afterwards (see the class `Note`).

        Returns:
            The updated `Milestone`.

        """
        await self._execute(
            self._MILESTONE_EDIT_MUTATION,
            {"input": {"milestoneId": milestone_id, "completed": True}},
        )
        return await self._get(goal_id, milestone_id)

    async def delete(self, milestone_id: int) -> None:
        """Delete (soft-delete) a milestone.

        Args:
            milestone_id: The ID of the milestone to delete.

        """
        await self._run_mutation(
            self._MILESTONE_DELETE_MUTATION,
            {"milestoneId": milestone_id},
            root_field="DeleteMilestone",
            action="delete milestone",
        )

    async def _get(self, goal_id: int, milestone_id: int) -> Milestone:
        """Re-read a single milestone through its parent goal.

        Returns:
            The `Milestone` model instance.

        Raises:
            GraphQLError: If the milestone is not found under the goal.

        """
        data = await self._execute(
            self._MILESTONE_BY_ID_QUERY,
            {"goalId": goal_id, "milestoneId": milestone_id},
        )
        nodes = dig_nodes(data, "goal", "milestones")
        if not nodes:
            raise GraphQLError(
                f"milestone {milestone_id} not found under goal {goal_id}"
            )
        return self._transform_milestone(nodes[0])
