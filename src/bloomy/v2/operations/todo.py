"""To-do operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from datetime import UTC, date, datetime, timedelta
from typing import Any

from ..base import (
    MUTATION_RESULT_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    dig_nodes,
    extract_notes,
)
from ..models import Todo

_TODO_FIELDS = """
id
title
dueDate
completed
completedTimestamp
archived
archivedTimestamp
dateCreated
notesId
notesText
localHtml
collaborationEnabled
assignee { id fullName }
meeting { id name }
"""


class TodoOperationsMixin:
    """Shared GraphQL documents and response transforms for to-do operations."""

    _TODO_DETAILS_QUERY = f"""
    query($id: Long!) {{
      todo(id: $id) {{
        {_TODO_FIELDS}
      }}
    }}
    """

    # `meeting.todos` returns EVERY to-do ever attached to the meeting,
    # including archived and soft-deleted ones (unlike `meeting.issues`,
    # which drops solved/archived issues server-side), so a single query
    # with a client-built `where` filter covers every combination of
    # `include_completed`/`include_archived` here.
    _TODO_LIST_MEETING_QUERY = f"""
    query($meetingId: Long!, $where: TodoQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        todos(where: $where, order: [{{ dueDate: ASC }}]) {{
          nodes {{
            {_TODO_FIELDS}
          }}
        }}
      }}
    }}
    """

    # The root `todos(userId)` connection already excludes archived to-dos
    # unconditionally, server-side (it is built from `CloseTime == null`),
    # so `include_archived` has no effect here; see `list()`.
    _TODO_LIST_USER_QUERY = f"""
    query($userId: Long!, $where: TodoQueryModelFilterInput) {{
      todos(userId: $userId, where: $where, order: [{{ dueDate: ASC }}]) {{
        nodes {{
          {_TODO_FIELDS}
        }}
      }}
    }}
    """

    _TODO_CREATE_MUTATION = """
    mutation($input: TodoCreateModelInput!) {
      CreateTodo(input: $input) {
        id
      }
    }
    """

    _TODO_EDIT_MUTATION = f"""
    mutation($input: TodoEditModelInput!) {{
      EditTodo(input: $input) {{
        {MUTATION_RESULT_FIELDS}
      }}
    }}
    """

    def _todo_list_where(
        self, *, include_completed: bool, include_archived: bool
    ) -> dict[str, Any] | None:
        """Build the `where` filter for a to-do list connection.

        Returns:
            A `TodoQueryModelFilterInput`-shaped dictionary, or `None` for no
            filter (list everything).

        """
        conditions: list[dict[str, Any]] = []
        if not include_completed:
            conditions.append({"completed": {"eq": False}})
        if not include_archived:
            conditions.append({"archived": {"eq": False}})
        return {"and": conditions} if conditions else None

    def _default_due_date(self) -> date:
        """Compute the default due date: 7 days from today, 00:00 UTC.

        Matches the web app's own default for a new to-do.

        Returns:
            A `date` 7 days from today (UTC).

        """
        return datetime.now(tz=UTC).date() + timedelta(days=7)

    def _transform_todo(self, data: dict[str, Any]) -> Todo:
        """Transform a raw GraphQL to-do object into a `Todo` model.

        Returns:
            A `Todo` model instance.

        """
        return Todo(**data, notes=extract_notes(data))


class TodoOperations(GraphQLOperations, TodoOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to to-dos."""

    def details(self, todo_id: int) -> Todo:
        """Get details for a to-do.

        Args:
            todo_id: The ID of the to-do.

        Returns:
            A `Todo` model instance.

        Example:
            ```python
            client.v2.todo.details(123)
            # Returns: Todo(id=123, title='To-do Title', ...)
            ```

        """
        data = self._execute(self._TODO_DETAILS_QUERY, {"id": todo_id})
        return self._transform_todo(data["todo"])

    def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        include_completed: bool = False,
        include_archived: bool = False,
    ) -> builtins.list[Todo]:
        """List to-dos for a meeting or a user.

        Args:
            meeting_id: The ID of the meeting to list to-dos for.
            user_id: The ID of the user to list to-dos for. Defaults to the
                current user when neither `meeting_id` nor `user_id` is
                given.
            include_completed: If `True`, also include completed to-dos.
            include_archived: If `True`, also include archived to-dos. Has
                no effect when listing by `user_id`: the underlying
                `todos(userId)` query excludes archived to-dos
                unconditionally, server-side.

        Returns:
            A list of `Todo` model instances, ordered by due date.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        Example:
            ```python
            client.v2.todo.list(meeting_id=349524)
            # Returns: [Todo(id=1, title='To-do 1', ...), ...]
            ```

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        where = self._todo_list_where(
            include_completed=include_completed, include_archived=include_archived
        )

        if meeting_id is not None:
            data = self._execute(
                self._TODO_LIST_MEETING_QUERY,
                {"meetingId": meeting_id, "where": where},
            )
            nodes = dig_nodes(data, "meeting", "todos")
            return [self._transform_todo(node) for node in nodes]

        if user_id is None:
            user_id = self.user_id
        data = self._execute(
            self._TODO_LIST_USER_QUERY, {"userId": user_id, "where": where}
        )
        nodes = dig_nodes(data, "todos")
        return [self._transform_todo(node) for node in nodes]

    def create(
        self,
        title: str,
        meeting_id: int | None = None,
        user_id: int | None = None,
        due_date: datetime | date | float | int | None = None,
        notes: str | None = None,
    ) -> Todo:
        """Create a new to-do.

        Args:
            title: The title of the to-do.
            meeting_id: The ID of the meeting to create the to-do in. Omit
                for a personal to-do (`meetingRecurrenceId` is sent as
                `null`).
            user_id: The ID of the to-do owner (defaults to the current
                user). Ignored by the API for a personal to-do, which is
                always assigned to the caller.
            due_date: The due date. Defaults to 7 days from today at 00:00
                UTC, matching the web app's own default.
            notes: Description text for the to-do.

        Returns:
            The newly created `Todo`.

        Example:
            ```python
            client.v2.todo.create("New To-do", meeting_id=349524)
            # Returns: Todo(id=456, title='New To-do', ...)
            ```

        """
        if user_id is None:
            user_id = self.user_id
        if due_date is None:
            due_date = self._default_due_date()

        input_: dict[str, Any] = {
            "title": title,
            "assigneeId": user_id,
            "meetingRecurrenceId": meeting_id,
            "dueDate": self._to_timestamp(due_date),
        }
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = self._execute(self._TODO_CREATE_MUTATION, {"input": input_})
        return self.details(data["CreateTodo"]["id"])

    def update(
        self,
        todo_id: int,
        *,
        title: str | None = None,
        due_date: datetime | date | float | int | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Todo:
        """Update an existing to-do.

        Args:
            todo_id: The ID of the to-do to update.
            title: New title for the to-do.
            due_date: New due date for the to-do. The due date cannot be
                cleared, only changed.
            user_id: New owner for the to-do.
            notes: New description text for the to-do.

        Returns:
            The updated `Todo`.

        Raises:
            ValueError: If no update fields are provided.

        Example:
            ```python
            client.v2.todo.update(123, title="New Title")
            # Returns: Todo(id=123, title='New Title', ...)
            ```

        """
        if title is None and due_date is None and user_id is None and notes is None:
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"todoId": todo_id}
        if title is not None:
            input_["title"] = title
        if due_date is not None:
            input_["dueDate"] = self._to_timestamp(due_date)
        if user_id is not None:
            input_["assigneeId"] = user_id
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": input_},
            root_field="EditTodo",
            action="update todo",
        )
        return self.details(todo_id)

    def complete(self, todo_id: int) -> Todo:
        """Mark a to-do as complete.

        Args:
            todo_id: The ID of the to-do to complete.

        Returns:
            The updated `Todo`.

        """
        self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "completedTimestamp": self._now_timestamp()}},
            root_field="EditTodo",
            action="complete todo",
        )
        return self.details(todo_id)

    def reopen(self, todo_id: int) -> Todo:
        """Reopen a completed to-do.

        Note:
            Sends `completedTimestamp: null` explicitly: `EditTodo`
            distinguishes an omitted field (no change) from an explicit
            `null` (clear it).

        Args:
            todo_id: The ID of the to-do to reopen.

        Returns:
            The updated `Todo`.

        """
        self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "completedTimestamp": None}},
            root_field="EditTodo",
            action="reopen todo",
        )
        return self.details(todo_id)

    def archive(self, todo_id: int) -> Todo:
        """Archive a to-do.

        Args:
            todo_id: The ID of the to-do to archive.

        Returns:
            The updated `Todo`.

        """
        self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "archivedTimestamp": self._now_timestamp()}},
            root_field="EditTodo",
            action="archive todo",
        )
        return self.details(todo_id)

    def restore(self, todo_id: int) -> Todo:
        """Restore an archived to-do.

        Note:
            Sends `archivedTimestamp: null` explicitly: `EditTodo`
            distinguishes an omitted field (no change) from an explicit
            `null` (clear it).

        Args:
            todo_id: The ID of the to-do to restore.

        Returns:
            The updated `Todo`.

        """
        self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "archivedTimestamp": None}},
            root_field="EditTodo",
            action="restore todo",
        )
        return self.details(todo_id)


class AsyncTodoOperations(AsyncGraphQLOperations, TodoOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to to-dos."""

    async def details(self, todo_id: int) -> Todo:
        """Get details for a to-do.

        Args:
            todo_id: The ID of the to-do.

        Returns:
            A `Todo` model instance.

        """
        data = await self._execute(self._TODO_DETAILS_QUERY, {"id": todo_id})
        return self._transform_todo(data["todo"])

    async def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        include_completed: bool = False,
        include_archived: bool = False,
    ) -> builtins.list[Todo]:
        """List to-dos for a meeting or a user.

        Args:
            meeting_id: The ID of the meeting to list to-dos for.
            user_id: The ID of the user to list to-dos for. Defaults to the
                current user when neither `meeting_id` nor `user_id` is
                given.
            include_completed: If `True`, also include completed to-dos.
            include_archived: If `True`, also include archived to-dos. Has
                no effect when listing by `user_id`: the underlying
                `todos(userId)` query excludes archived to-dos
                unconditionally, server-side.

        Returns:
            A list of `Todo` model instances, ordered by due date.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        where = self._todo_list_where(
            include_completed=include_completed, include_archived=include_archived
        )

        if meeting_id is not None:
            data = await self._execute(
                self._TODO_LIST_MEETING_QUERY,
                {"meetingId": meeting_id, "where": where},
            )
            nodes = dig_nodes(data, "meeting", "todos")
            return [self._transform_todo(node) for node in nodes]

        if user_id is None:
            user_id = await self.get_user_id()
        data = await self._execute(
            self._TODO_LIST_USER_QUERY, {"userId": user_id, "where": where}
        )
        nodes = dig_nodes(data, "todos")
        return [self._transform_todo(node) for node in nodes]

    async def create(
        self,
        title: str,
        meeting_id: int | None = None,
        user_id: int | None = None,
        due_date: datetime | date | float | int | None = None,
        notes: str | None = None,
    ) -> Todo:
        """Create a new to-do.

        Args:
            title: The title of the to-do.
            meeting_id: The ID of the meeting to create the to-do in. Omit
                for a personal to-do (`meetingRecurrenceId` is sent as
                `null`).
            user_id: The ID of the to-do owner (defaults to the current
                user). Ignored by the API for a personal to-do, which is
                always assigned to the caller.
            due_date: The due date. Defaults to 7 days from today at 00:00
                UTC, matching the web app's own default.
            notes: Description text for the to-do.

        Returns:
            The newly created `Todo`.

        """
        if user_id is None:
            user_id = await self.get_user_id()
        if due_date is None:
            due_date = self._default_due_date()

        input_: dict[str, Any] = {
            "title": title,
            "assigneeId": user_id,
            "meetingRecurrenceId": meeting_id,
            "dueDate": self._to_timestamp(due_date),
        }
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = await self._execute(self._TODO_CREATE_MUTATION, {"input": input_})
        return await self.details(data["CreateTodo"]["id"])

    async def update(
        self,
        todo_id: int,
        *,
        title: str | None = None,
        due_date: datetime | date | float | int | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Todo:
        """Update an existing to-do.

        Args:
            todo_id: The ID of the to-do to update.
            title: New title for the to-do.
            due_date: New due date for the to-do. The due date cannot be
                cleared, only changed.
            user_id: New owner for the to-do.
            notes: New description text for the to-do.

        Returns:
            The updated `Todo`.

        Raises:
            ValueError: If no update fields are provided.

        """
        if title is None and due_date is None and user_id is None and notes is None:
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"todoId": todo_id}
        if title is not None:
            input_["title"] = title
        if due_date is not None:
            input_["dueDate"] = self._to_timestamp(due_date)
        if user_id is not None:
            input_["assigneeId"] = user_id
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        await self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": input_},
            root_field="EditTodo",
            action="update todo",
        )
        return await self.details(todo_id)

    async def complete(self, todo_id: int) -> Todo:
        """Mark a to-do as complete.

        Args:
            todo_id: The ID of the to-do to complete.

        Returns:
            The updated `Todo`.

        """
        await self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "completedTimestamp": self._now_timestamp()}},
            root_field="EditTodo",
            action="complete todo",
        )
        return await self.details(todo_id)

    async def reopen(self, todo_id: int) -> Todo:
        """Reopen a completed to-do.

        Note:
            Sends `completedTimestamp: null` explicitly: `EditTodo`
            distinguishes an omitted field (no change) from an explicit
            `null` (clear it).

        Args:
            todo_id: The ID of the to-do to reopen.

        Returns:
            The updated `Todo`.

        """
        await self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "completedTimestamp": None}},
            root_field="EditTodo",
            action="reopen todo",
        )
        return await self.details(todo_id)

    async def archive(self, todo_id: int) -> Todo:
        """Archive a to-do.

        Args:
            todo_id: The ID of the to-do to archive.

        Returns:
            The updated `Todo`.

        """
        await self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "archivedTimestamp": self._now_timestamp()}},
            root_field="EditTodo",
            action="archive todo",
        )
        return await self.details(todo_id)

    async def restore(self, todo_id: int) -> Todo:
        """Restore an archived to-do.

        Note:
            Sends `archivedTimestamp: null` explicitly: `EditTodo`
            distinguishes an omitted field (no change) from an explicit
            `null` (clear it).

        Args:
            todo_id: The ID of the to-do to restore.

        Returns:
            The updated `Todo`.

        """
        await self._run_mutation(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, "archivedTimestamp": None}},
            root_field="EditTodo",
            action="restore todo",
        )
        return await self.details(todo_id)
