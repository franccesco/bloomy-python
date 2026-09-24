"""Goal (rock) operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ...exceptions import GraphQLError
from ..base import (
    MILESTONES_CONNECTION,
    NOTES_FIELDS,
    USER_REF_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    TimeInput,
    compact,
    default_due_date,
    dig_nodes,
    to_timestamp,
)
from ..models import Goal, GoalStatus

_GOAL_FIELDS = f"""
id
title
status
dueDate
archived
archivedTimestamp
dateCreated
{NOTES_FIELDS}
{USER_REF_FIELDS}
meetings {{
  nodes {{
    id
    name
  }}
}}
{MILESTONES_CONNECTION}
"""

_GOALS_CONNECTION = f"""
goals(where: $where, order: [{{ dueDate: ASC }}]) {{
  nodes {{
    {_GOAL_FIELDS}
  }}
}}
"""


class GoalOperationsMixin:
    """GraphQL documents, inputs, and response parsing shared by goal operations."""

    _GOAL_DETAILS_QUERY = f"""
    query($id: Long!) {{
      goal(id: $id) {{
        {_GOAL_FIELDS}
      }}
    }}
    """

    _GOAL_MEETING_LIST_QUERY = f"""
    query($meetingId: Long!, $where: GoalQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        {_GOALS_CONNECTION}
      }}
    }}
    """

    # Root `goals(userId)` drops archived goals whatever `where` says, so the
    # user list reads `user(id){ goals }` instead.
    _GOAL_USER_LIST_QUERY = f"""
    query($userId: Long!, $where: GoalQueryModelFilterInput) {{
      user(id: $userId) {{
        {_GOALS_CONNECTION}
      }}
    }}
    """

    _GOAL_CREATE_MUTATION = """
    mutation($input: GoalCreateModelInput!) {
      CreateGoal(input: $input) {
        id
      }
    }
    """

    _GOAL_EDIT_MUTATION = """
    mutation($input: GoalEditModelInput!) {
      EditGoal(input: $input) {
        id
      }
    }
    """

    @classmethod
    def _goal_list_request(
        cls, meeting_id: int | None, user_id: int | None, *, include_archived: bool
    ) -> tuple[str, dict[str, Any]]:
        """Pick the list document for a meeting or a user, with its variables.

        Returns:
            The query document and its variables.

        """
        where = None if include_archived else {"and": [{"archived": {"eq": False}}]}
        if meeting_id is not None:
            return cls._GOAL_MEETING_LIST_QUERY, {
                "meetingId": meeting_id,
                "where": where,
            }
        return cls._GOAL_USER_LIST_QUERY, {"userId": user_id, "where": where}

    @staticmethod
    def _goals_from(data: dict[str, Any]) -> list[Goal]:
        """Validate the goals of a meeting or user list response.

        A response carries either `meeting` or `user`; the absent one reads
        as empty.

        Returns:
            The goals, ordered by due date.

        """
        nodes = [
            *dig_nodes(data, "meeting", "goals"),
            *dig_nodes(data, "user", "goals"),
        ]
        return [Goal.model_validate(node) for node in nodes]

    @staticmethod
    def _goal_milestone_input(item: dict[str, Any] | tuple[Any, ...]) -> dict[str, Any]:
        """Build a `Goal_MilestoneCreateModelInput` from a `create()` milestone item.

        Args:
            item: Either `{"title": ..., "due_date": ..., "completed": ...}`
                (`completed` optional) or a `(title, due_date)` /
                `(title, due_date, completed)` tuple.

        Returns:
            The input fields.

        """
        if isinstance(item, dict):
            title, due_date = item["title"], item["due_date"]
            completed = item.get("completed", False)
        else:
            title, due_date, *rest = item
            completed = rest[0] if rest else False
        return {
            "title": title,
            "dueDate": to_timestamp(due_date),
            "completed": completed,
        }

    @classmethod
    def _goal_create_input(
        cls,
        *,
        meeting_id: int,
        title: str,
        user_id: int,
        due_date: TimeInput | None,
        status: GoalStatus | str,
        milestones: list[dict[str, Any] | tuple[Any, ...]] | None,
    ) -> dict[str, Any]:
        """Build the `GoalCreateModelInput` fields, apart from notes.

        Returns:
            The input fields, with the due date defaulting to 90 days out.

        """
        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "dueDate": to_timestamp(
                default_due_date(90) if due_date is None else due_date
            ),
            "status": str(status),
            "meetingsAndPlans": [
                {"meetingId": meeting_id, "addToDepartmentPlan": False}
            ],
        }
        if milestones:
            input_["milestones"] = [
                cls._goal_milestone_input(item) for item in milestones
            ]
        return input_

    @staticmethod
    def _goal_edit_fields(
        *,
        title: str | None,
        status: GoalStatus | str | None,
        due_date: TimeInput | None,
        user_id: int | None,
    ) -> dict[str, Any]:
        """Build the `GoalEditModelInput` fields that were given, apart from notes.

        Returns:
            The non-`None` input fields.

        """
        return compact(
            title=title,
            status=None if status is None else str(status),
            dueDate=None if due_date is None else to_timestamp(due_date),
            assignee=user_id,
        )


class GoalOperations(GraphQLOperations, GoalOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to goals (rocks)."""

    def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        include_archived: bool = False,
    ) -> builtins.list[Goal]:
        """List goals for a meeting or a user.

        Args:
            meeting_id: List goals attached to this meeting.
            user_id: List goals owned by this user (defaults to the current
                user when both `meeting_id` and `user_id` are omitted).
            include_archived: If `True`, also include archived goals.

        Returns:
            A list of `Goal` model instances (each including its
            milestones), ordered by due date.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        Example:
            ```python
            client.v2.goal.list(349524)
            # Returns: [Goal(id=1, title='Ship v2', ...), ...]
            ```

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = self.user_id
        query, variables = self._goal_list_request(
            meeting_id, user_id, include_archived=include_archived
        )
        return self._goals_from(self._execute(query, variables))

    def details(self, goal_id: int) -> Goal:
        """Get details for a goal, including its milestones.

        Args:
            goal_id: The ID of the goal.

        Returns:
            A `Goal` model instance.

        Example:
            ```python
            client.v2.goal.details(5265048)
            # Returns: Goal(id=5265048, title='Ship v2', ...)
            ```

        """
        data = self._execute(self._GOAL_DETAILS_QUERY, {"id": goal_id})
        return Goal.model_validate(
            self._one(data, "goal", label="Goal", entity_id=goal_id)
        )

    def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        due_date: TimeInput | None = None,
        status: GoalStatus | str = GoalStatus.ON_TRACK,
        notes: str | None = None,
        milestones: builtins.list[dict[str, Any] | tuple[Any, ...]] | None = None,
    ) -> Goal:
        """Create a new goal.

        Args:
            meeting_id: The ID of the meeting to attach the goal to.
            title: The title of the goal.
            user_id: The ID of the goal owner (defaults to the current user).
            due_date: The due date, as a `datetime`, `date`, or unix
                timestamp (seconds). Defaults to 90 days from today (00:00 UTC).
            status: The initial status.
            notes: Description text for the goal.
            milestones: Milestones to create alongside the goal, each either
                `{"title": ..., "due_date": ..., "completed": ...}`
                (`completed` optional, defaults to `False`) or a
                `(title, due_date)` / `(title, due_date, completed)` tuple.

        Returns:
            The newly created `Goal`.

        Example:
            ```python
            client.v2.goal.create(349524, "Ship v2", notes="Launch details")
            # Returns: Goal(id=456, title='Ship v2', ...)
            ```

        """
        if user_id is None:
            user_id = self.user_id
        input_ = self._goal_create_input(
            meeting_id=meeting_id,
            title=title,
            user_id=user_id,
            due_date=due_date,
            status=status,
            milestones=milestones,
        )
        result = self._mutate(
            self._GOAL_CREATE_MUTATION,
            {"input": {**input_, **self._notes_input(notes)}},
            root_field="CreateGoal",
            action="create goal",
        )
        return self.details(result["id"])

    def update(
        self,
        goal_id: int,
        *,
        title: str | None = None,
        status: GoalStatus | str | None = None,
        due_date: TimeInput | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Goal:
        """Update an existing goal.

        Args:
            goal_id: The ID of the goal to update.
            title: New title for the goal.
            status: New status for the goal.
            due_date: New due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            user_id: New owner for the goal.
            notes: New description text for the goal.

        Returns:
            The updated `Goal`.

        Raises:
            ValueError: If no update fields are provided.

        Example:
            ```python
            client.v2.goal.update(5265048, title="New title")
            # Returns: Goal(id=5265048, title='New title', ...)
            ```

        """
        fields = self._goal_edit_fields(
            title=title, status=status, due_date=due_date, user_id=user_id
        )
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(self._notes_input(notes))
        return self._edit(goal_id, fields, action="update goal")

    def archive(self, goal_id: int) -> Goal:
        """Archive a goal.

        Note:
            Verified live: `EditGoal{archived: true}` can report success
            without archiving the goal, because the server discards the
            archive step's exceptions. This re-reads the goal and raises
            `GraphQLError` if it is still not archived.

        Args:
            goal_id: The ID of the goal to archive.

        Returns:
            The updated `Goal`.

        Raises:
            GraphQLError: If the goal is still not archived after the edit.

        """
        result = self._edit(goal_id, {"archived": True}, action="archive goal")
        if not result.archived:
            raise GraphQLError(
                f"archive goal {goal_id} failed: goal is still not archived"
            )
        return result

    def restore(self, goal_id: int) -> Goal:
        """Restore an archived goal.

        Note:
            Verified live against production: `EditGoal{archived: false}`
            reliably un-archives the goal and re-attaches the meeting links
            that were detached within +/-3 minutes of the archive.

        Args:
            goal_id: The ID of the goal to restore.

        Returns:
            The updated `Goal`.

        """
        return self._edit(goal_id, {"archived": False}, action="restore goal")

    def _edit(self, goal_id: int, fields: dict[str, Any], *, action: str) -> Goal:
        """Run `EditGoal` with `fields`, then re-read the goal.

        Returns:
            The updated `Goal`.

        """
        self._mutate(
            self._GOAL_EDIT_MUTATION,
            {"input": {"goalId": goal_id, **fields}},
            root_field="EditGoal",
            action=action,
        )
        return self.details(goal_id)


class AsyncGoalOperations(AsyncGraphQLOperations, GoalOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to goals (rocks)."""

    async def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        include_archived: bool = False,
    ) -> builtins.list[Goal]:
        """List goals for a meeting or a user.

        Args:
            meeting_id: List goals attached to this meeting.
            user_id: List goals owned by this user (defaults to the current
                user when both `meeting_id` and `user_id` are omitted).
            include_archived: If `True`, also include archived goals.

        Returns:
            A list of `Goal` model instances (each including its
            milestones), ordered by due date.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = await self.get_user_id()
        query, variables = self._goal_list_request(
            meeting_id, user_id, include_archived=include_archived
        )
        return self._goals_from(await self._execute(query, variables))

    async def details(self, goal_id: int) -> Goal:
        """Get details for a goal, including its milestones.

        Args:
            goal_id: The ID of the goal.

        Returns:
            A `Goal` model instance.

        """
        data = await self._execute(self._GOAL_DETAILS_QUERY, {"id": goal_id})
        return Goal.model_validate(
            self._one(data, "goal", label="Goal", entity_id=goal_id)
        )

    async def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        due_date: TimeInput | None = None,
        status: GoalStatus | str = GoalStatus.ON_TRACK,
        notes: str | None = None,
        milestones: builtins.list[dict[str, Any] | tuple[Any, ...]] | None = None,
    ) -> Goal:
        """Create a new goal.

        Args:
            meeting_id: The ID of the meeting to attach the goal to.
            title: The title of the goal.
            user_id: The ID of the goal owner (defaults to the current user).
            due_date: The due date, as a `datetime`, `date`, or unix
                timestamp (seconds). Defaults to 90 days from today (00:00 UTC).
            status: The initial status.
            notes: Description text for the goal.
            milestones: Milestones to create alongside the goal, each either
                `{"title": ..., "due_date": ..., "completed": ...}`
                (`completed` optional, defaults to `False`) or a
                `(title, due_date)` / `(title, due_date, completed)` tuple.

        Returns:
            The newly created `Goal`.

        """
        if user_id is None:
            user_id = await self.get_user_id()
        input_ = self._goal_create_input(
            meeting_id=meeting_id,
            title=title,
            user_id=user_id,
            due_date=due_date,
            status=status,
            milestones=milestones,
        )
        result = await self._mutate(
            self._GOAL_CREATE_MUTATION,
            {"input": {**input_, **await self._notes_input(notes)}},
            root_field="CreateGoal",
            action="create goal",
        )
        return await self.details(result["id"])

    async def update(
        self,
        goal_id: int,
        *,
        title: str | None = None,
        status: GoalStatus | str | None = None,
        due_date: TimeInput | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Goal:
        """Update an existing goal.

        Args:
            goal_id: The ID of the goal to update.
            title: New title for the goal.
            status: New status for the goal.
            due_date: New due date, as a `datetime`, `date`, or unix
                timestamp (seconds).
            user_id: New owner for the goal.
            notes: New description text for the goal.

        Returns:
            The updated `Goal`.

        Raises:
            ValueError: If no update fields are provided.

        """
        fields = self._goal_edit_fields(
            title=title, status=status, due_date=due_date, user_id=user_id
        )
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(await self._notes_input(notes))
        return await self._edit(goal_id, fields, action="update goal")

    async def archive(self, goal_id: int) -> Goal:
        """Archive a goal.

        Note:
            Verified live: `EditGoal{archived: true}` can report success
            without archiving the goal, because the server discards the
            archive step's exceptions. This re-reads the goal and raises
            `GraphQLError` if it is still not archived.

        Args:
            goal_id: The ID of the goal to archive.

        Returns:
            The updated `Goal`.

        Raises:
            GraphQLError: If the goal is still not archived after the edit.

        """
        result = await self._edit(goal_id, {"archived": True}, action="archive goal")
        if not result.archived:
            raise GraphQLError(
                f"archive goal {goal_id} failed: goal is still not archived"
            )
        return result

    async def restore(self, goal_id: int) -> Goal:
        """Restore an archived goal.

        Note:
            Verified live against production: `EditGoal{archived: false}`
            reliably un-archives the goal and re-attaches the meeting links
            that were detached within +/-3 minutes of the archive.

        Args:
            goal_id: The ID of the goal to restore.

        Returns:
            The updated `Goal`.

        """
        return await self._edit(goal_id, {"archived": False}, action="restore goal")

    async def _edit(self, goal_id: int, fields: dict[str, Any], *, action: str) -> Goal:
        """Run `EditGoal` with `fields`, then re-read the goal.

        Returns:
            The updated `Goal`.

        """
        await self._mutate(
            self._GOAL_EDIT_MUTATION,
            {"input": {"goalId": goal_id, **fields}},
            root_field="EditGoal",
            action=action,
        )
        return await self.details(goal_id)
