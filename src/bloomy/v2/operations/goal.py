"""Goal (rock) operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from datetime import date, datetime, timedelta
from typing import Any

from ...exceptions import GraphQLError
from ..base import AsyncGraphQLOperations, GraphQLOperations, dig_nodes, extract_notes
from ..models import Goal, GoalStatus, MeetingRef, Milestone

# Kept in sync with `milestone.py`'s `_MILESTONE_FIELDS` (duplicated rather
# than imported, to keep the two entity modules independent). `dateDeleted`
# is already filtered server-side; the explicit filter matches the web app's
# own query.
_GOAL_MILESTONE_FIELDS = "id goalId title dueDate completed status dateCreated"

_GOAL_FIELDS = f"""
id
title
status
dueDate
archived
archivedTimestamp
dateCreated
notesId
notesText
localHtml
collaborationEnabled
assignee {{ id fullName }}
meetings {{
  nodes {{
    id
    name
  }}
}}
milestones(
  where: {{ and: [{{ dateDeleted: {{ eq: null }} }}] }}
  order: [{{ dueDate: ASC }}]
) {{
  nodes {{
    {_GOAL_MILESTONE_FIELDS}
  }}
}}
"""


class GoalOperationsMixin:
    """Shared GraphQL documents and response transforms for goal operations."""

    _GOAL_DETAILS_QUERY = f"""
    query($id: Long!) {{
      goal(id: $id) {{
        {_GOAL_FIELDS}
      }}
    }}
    """

    _GOAL_LIST_BY_MEETING_QUERY = f"""
    query($meetingId: Long!, $where: GoalQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        goals(where: $where, order: [{{ dueDate: ASC }}]) {{
          nodes {{
            {_GOAL_FIELDS}
          }}
        }}
      }}
    }}
    """

    # `goals(userId)` (the root field) unconditionally excludes archived
    # goals server-side regardless of `where` (verified live: a `where:
    # {archived: {eq: true}}` filter still returns 0 results for a user with
    # hundreds of archived goals). `user(id){ goals }` respects the filter
    # (verified live), so it is used here instead to make `include_archived`
    # actually work.
    _GOAL_LIST_BY_USER_QUERY = f"""
    query($userId: Long!, $where: GoalQueryModelFilterInput) {{
      user(id: $userId) {{
        goals(where: $where, order: [{{ dueDate: ASC }}]) {{
          nodes {{
            {_GOAL_FIELDS}
          }}
        }}
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

    # CreateGoal/EditGoal return only `IdModel { id }` (verified live), not
    # the `{success message errorDetails}` shape `_run_mutation` expects. A
    # failed mutation raises through the standard `errors` array instead
    # (an invalid input throws server-side, including `IdModel(0)` on a
    # failed create), so these are executed with plain `_execute`. `archive`
    # additionally re-reads the goal, because `EditGoal{archived: true}` can
    # report success without archiving anything (see `archive`'s docstring).
    _GOAL_EDIT_MUTATION = """
    mutation($input: GoalEditModelInput!) {
      EditGoal(input: $input) {
        id
      }
    }
    """

    def _goal_where(self, *, include_archived: bool) -> dict[str, Any] | None:
        """Build the `where` filter for a goal list connection.

        Returns:
            A `GoalQueryModelFilterInput`-shaped dictionary, or `None` to
            leave the connection unfiltered (both archived and active).

        """
        if include_archived:
            return None
        return {"and": [{"archived": {"eq": False}}]}

    def _parse_milestone_item(
        self, item: dict[str, Any] | tuple[Any, ...]
    ) -> tuple[Any, Any, bool]:
        """Parse a `create()` milestone item into `(title, due_date, completed)`.

        `due_date` is returned as given (not yet converted to a unix
        timestamp): that conversion needs `_to_timestamp`, a base-class
        helper this mixin does not itself have access to (see
        `GraphQLOperations`/`AsyncGraphQLOperations.create`, which call it
        on the parsed result instead).

        Args:
            item: Either `{"title": ..., "due_date": ..., "completed": ...}`
                (`completed` optional) or a `(title, due_date)` /
                `(title, due_date, completed)` tuple.

        Returns:
            A `(title, due_date, completed)` tuple.

        """
        if isinstance(item, dict):
            return item["title"], item["due_date"], item.get("completed", False)
        title, due_date, *rest = item
        return title, due_date, (rest[0] if rest else False)

    def _transform_goal(self, data: dict[str, Any]) -> Goal:
        """Transform a raw GraphQL goal object into a `Goal` model.

        Returns:
            A `Goal` model instance.

        """
        milestone_nodes = dig_nodes(data, "milestones")
        meeting_nodes = dig_nodes(data, "meetings")
        rest = {
            key: value
            for key, value in data.items()
            if key not in ("milestones", "meetings")
        }
        return Goal(
            **rest,
            notes=extract_notes(data),
            milestones=[Milestone(**node) for node in milestone_nodes],
            meetings=[MeetingRef(**node) for node in meeting_nodes],
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

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        where = self._goal_where(include_archived=include_archived)

        if meeting_id is not None:
            data = self._execute(
                self._GOAL_LIST_BY_MEETING_QUERY,
                {"meetingId": meeting_id, "where": where},
            )
            nodes = dig_nodes(data, "meeting", "goals")
        else:
            if user_id is None:
                user_id = self.user_id
            data = self._execute(
                self._GOAL_LIST_BY_USER_QUERY, {"userId": user_id, "where": where}
            )
            nodes = dig_nodes(data, "user", "goals")

        return [self._transform_goal(node) for node in nodes]

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
        return self._transform_goal(data["goal"])

    def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        due_date: datetime | date | float | int | None = None,
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
        if due_date is None:
            due_date = date.today() + timedelta(days=90)

        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "dueDate": self._to_timestamp(due_date),
            "status": str(status),
            "meetingsAndPlans": [
                {"meetingId": meeting_id, "addToDepartmentPlan": False}
            ],
        }
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True
        if milestones:
            input_["milestones"] = [
                {
                    "title": parsed_title,
                    "dueDate": self._to_timestamp(parsed_due_date),
                    "completed": parsed_completed,
                }
                for parsed_title, parsed_due_date, parsed_completed in (
                    self._parse_milestone_item(item) for item in milestones
                )
            ]

        data = self._execute(self._GOAL_CREATE_MUTATION, {"input": input_})
        return self.details(data["CreateGoal"]["id"])

    def update(
        self,
        goal_id: int,
        *,
        title: str | None = None,
        status: GoalStatus | str | None = None,
        due_date: datetime | date | float | int | None = None,
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
        if (
            title is None
            and status is None
            and due_date is None
            and user_id is None
            and notes is None
        ):
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"goalId": goal_id}
        if title is not None:
            input_["title"] = title
        if status is not None:
            input_["status"] = str(status)
        if due_date is not None:
            input_["dueDate"] = self._to_timestamp(due_date)
        if user_id is not None:
            input_["assignee"] = user_id
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        self._execute(self._GOAL_EDIT_MUTATION, {"input": input_})
        return self.details(goal_id)

    def archive(self, goal_id: int) -> Goal:
        """Archive a goal.

        Note:
            Verified live: `EditGoal{archived: true}` can report success
            without archiving anything, because the server detaches the goal
            from its meetings through an un-awaited call whose exceptions
            are lost, and the archive step itself is wrapped in a bare
            `try/catch`. This re-reads the goal afterwards and raises
            `GraphQLError` if it is still not archived.

        Args:
            goal_id: The ID of the goal to archive.

        Returns:
            The updated `Goal`.

        Raises:
            GraphQLError: If the goal is still not archived after the edit.

        """
        self._execute(
            self._GOAL_EDIT_MUTATION, {"input": {"goalId": goal_id, "archived": True}}
        )
        result = self.details(goal_id)
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
        self._execute(
            self._GOAL_EDIT_MUTATION, {"input": {"goalId": goal_id, "archived": False}}
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

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        where = self._goal_where(include_archived=include_archived)

        if meeting_id is not None:
            data = await self._execute(
                self._GOAL_LIST_BY_MEETING_QUERY,
                {"meetingId": meeting_id, "where": where},
            )
            nodes = dig_nodes(data, "meeting", "goals")
        else:
            if user_id is None:
                user_id = await self.get_user_id()
            data = await self._execute(
                self._GOAL_LIST_BY_USER_QUERY, {"userId": user_id, "where": where}
            )
            nodes = dig_nodes(data, "user", "goals")

        return [self._transform_goal(node) for node in nodes]

    async def details(self, goal_id: int) -> Goal:
        """Get details for a goal, including its milestones.

        Args:
            goal_id: The ID of the goal.

        Returns:
            A `Goal` model instance.

        """
        data = await self._execute(self._GOAL_DETAILS_QUERY, {"id": goal_id})
        return self._transform_goal(data["goal"])

    async def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        due_date: datetime | date | float | int | None = None,
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
        if due_date is None:
            due_date = date.today() + timedelta(days=90)

        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "dueDate": self._to_timestamp(due_date),
            "status": str(status),
            "meetingsAndPlans": [
                {"meetingId": meeting_id, "addToDepartmentPlan": False}
            ],
        }
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True
        if milestones:
            input_["milestones"] = [
                {
                    "title": parsed_title,
                    "dueDate": self._to_timestamp(parsed_due_date),
                    "completed": parsed_completed,
                }
                for parsed_title, parsed_due_date, parsed_completed in (
                    self._parse_milestone_item(item) for item in milestones
                )
            ]

        data = await self._execute(self._GOAL_CREATE_MUTATION, {"input": input_})
        return await self.details(data["CreateGoal"]["id"])

    async def update(
        self,
        goal_id: int,
        *,
        title: str | None = None,
        status: GoalStatus | str | None = None,
        due_date: datetime | date | float | int | None = None,
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
        if (
            title is None
            and status is None
            and due_date is None
            and user_id is None
            and notes is None
        ):
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"goalId": goal_id}
        if title is not None:
            input_["title"] = title
        if status is not None:
            input_["status"] = str(status)
        if due_date is not None:
            input_["dueDate"] = self._to_timestamp(due_date)
        if user_id is not None:
            input_["assignee"] = user_id
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        await self._execute(self._GOAL_EDIT_MUTATION, {"input": input_})
        return await self.details(goal_id)

    async def archive(self, goal_id: int) -> Goal:
        """Archive a goal.

        Note:
            Verified live: `EditGoal{archived: true}` can report success
            without archiving anything, because the server detaches the goal
            from its meetings through an un-awaited call whose exceptions
            are lost, and the archive step itself is wrapped in a bare
            `try/catch`. This re-reads the goal afterwards and raises
            `GraphQLError` if it is still not archived.

        Args:
            goal_id: The ID of the goal to archive.

        Returns:
            The updated `Goal`.

        Raises:
            GraphQLError: If the goal is still not archived after the edit.

        """
        await self._execute(
            self._GOAL_EDIT_MUTATION, {"input": {"goalId": goal_id, "archived": True}}
        )
        result = await self.details(goal_id)
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
        await self._execute(
            self._GOAL_EDIT_MUTATION, {"input": {"goalId": goal_id, "archived": False}}
        )
        return await self.details(goal_id)
