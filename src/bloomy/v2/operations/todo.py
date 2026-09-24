"""To-do operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import (
    MEETING_REF_FIELDS,
    MUTATION_RESULT_FIELDS,
    NOTES_FIELDS,
    USER_REF_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    TimeInput,
    compact,
    default_due_date,
    dig_nodes,
    now_timestamp,
    to_timestamp,
)
from ..models import Todo

_TODO_FIELDS = f"""
id
title
dueDate
completed
completedTimestamp
archived
archivedTimestamp
dateCreated
{NOTES_FIELDS}
{USER_REF_FIELDS}
{MEETING_REF_FIELDS}
"""


class TodoOperationsMixin:
    """GraphQL documents, inputs, and response parsing shared by to-do operations."""

    _TODO_DETAILS_QUERY = f"""
    query($id: Long!) {{
      todo(id: $id) {{
        {_TODO_FIELDS}
      }}
    }}
    """

    # `todosActives` drops archived and deleted to-dos server-side but keeps
    # completed ones; `todos` returns every to-do ever attached to the meeting.
    _TODO_MEETING_LIST_QUERY = f"""
    query(
      $meetingId: Long!
      $where: TodoQueryModelFilterInput
      $includeArchived: Boolean!
    ) {{
      meeting(id: $meetingId) {{
        todosActives(where: $where, order: [{{ dueDate: ASC }}])
          @skip(if: $includeArchived) {{
          nodes {{
            {_TODO_FIELDS}
          }}
        }}
        todos(where: $where, order: [{{ dueDate: ASC }}])
          @include(if: $includeArchived) {{
          nodes {{
            {_TODO_FIELDS}
          }}
        }}
      }}
    }}
    """

    _TODO_USER_LIST_QUERY = f"""
    query($userId: Long!, $where: TodoQueryModelFilterInput) {{
      todos(userId: $userId, where: $where, order: [{{ dueDate: ASC }}]) {{
        nodes {{
          {_TODO_FIELDS}
        }}
      }}
    }}
    """

    _TODO_CREATE_MUTATION = f"""
    mutation($input: TodoCreateModelInput!) {{
      CreateTodo(input: $input) {{
        {_TODO_FIELDS}
      }}
    }}
    """

    # `EditTodo` leaves an omitted field unchanged and clears one sent as `null`.
    _TODO_EDIT_MUTATION = f"""
    mutation($input: TodoEditModelInput!) {{
      EditTodo(input: $input) {{
        {MUTATION_RESULT_FIELDS}
      }}
    }}
    """

    @classmethod
    def _todo_list_request(
        cls,
        meeting_id: int | None,
        user_id: int | None,
        *,
        include_completed: bool,
        include_archived: bool,
    ) -> tuple[str, dict[str, Any]]:
        """Pick the list document for a meeting or a user, with its variables.

        Returns:
            The query document and its variables.

        """
        where = None if include_completed else {"completed": {"eq": False}}
        if meeting_id is not None:
            return cls._TODO_MEETING_LIST_QUERY, {
                "meetingId": meeting_id,
                "where": where,
                "includeArchived": include_archived,
            }
        return cls._TODO_USER_LIST_QUERY, {"userId": user_id, "where": where}

    @staticmethod
    def _todos_from(data: dict[str, Any]) -> list[Todo]:
        """Validate the to-dos of a list query response.

        Each response carries exactly one of the three connections read here.

        Returns:
            The to-dos, ordered by due date.

        """
        nodes = [
            *dig_nodes(data, "todos"),
            *dig_nodes(data, "meeting", "todosActives"),
            *dig_nodes(data, "meeting", "todos"),
        ]
        return [Todo.model_validate(node) for node in nodes]

    @staticmethod
    def _todo_create_input(
        *,
        title: str,
        meeting_id: int | None,
        user_id: int,
        due_date: TimeInput | None,
    ) -> dict[str, Any]:
        """Build the `TodoCreateModelInput` fields, apart from notes.

        Returns:
            The input fields, with the due date defaulting to 7 days from
            today.

        """
        return {
            "title": title,
            "assigneeId": user_id,
            "meetingRecurrenceId": meeting_id,
            "dueDate": to_timestamp(
                default_due_date(7) if due_date is None else due_date
            ),
        }

    @staticmethod
    def _todo_edit_fields(
        *,
        title: str | None,
        due_date: TimeInput | None,
        user_id: int | None,
    ) -> dict[str, Any]:
        """Build the `TodoEditModelInput` fields that were given, apart from notes.

        Returns:
            The non-`None` input fields.

        """
        return compact(
            title=title,
            dueDate=None if due_date is None else to_timestamp(due_date),
            assigneeId=user_id,
        )


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
        return Todo.model_validate(
            self._one(data, "todo", label="Todo", entity_id=todo_id)
        )

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

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = self.user_id
        query, variables = self._todo_list_request(
            meeting_id,
            user_id,
            include_completed=include_completed,
            include_archived=include_archived,
        )
        return self._todos_from(self._execute(query, variables))

    def create(
        self,
        title: str,
        meeting_id: int | None = None,
        user_id: int | None = None,
        due_date: TimeInput | None = None,
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
        input_ = self._todo_create_input(
            title=title, meeting_id=meeting_id, user_id=user_id, due_date=due_date
        )
        result = self._mutate(
            self._TODO_CREATE_MUTATION,
            {"input": {**input_, **self._notes_input(notes)}},
            root_field="CreateTodo",
            action="create todo",
        )
        return Todo.model_validate(result)

    def update(
        self,
        todo_id: int,
        *,
        title: str | None = None,
        due_date: TimeInput | None = None,
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
        fields = self._todo_edit_fields(title=title, due_date=due_date, user_id=user_id)
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(self._notes_input(notes))
        return self._edit(todo_id, fields, action="update todo")

    def complete(self, todo_id: int) -> Todo:
        """Mark a to-do as complete.

        Args:
            todo_id: The ID of the to-do to complete.

        Returns:
            The updated `Todo`.

        """
        return self._edit(
            todo_id, {"completedTimestamp": now_timestamp()}, action="complete todo"
        )

    def reopen(self, todo_id: int) -> Todo:
        """Reopen a completed to-do.

        Args:
            todo_id: The ID of the to-do to reopen.

        Returns:
            The updated `Todo`.

        """
        return self._edit(todo_id, {"completedTimestamp": None}, action="reopen todo")

    def archive(self, todo_id: int) -> Todo:
        """Archive a to-do.

        Args:
            todo_id: The ID of the to-do to archive.

        Returns:
            The updated `Todo`.

        """
        return self._edit(
            todo_id, {"archivedTimestamp": now_timestamp()}, action="archive todo"
        )

    def restore(self, todo_id: int) -> Todo:
        """Restore an archived to-do.

        Args:
            todo_id: The ID of the to-do to restore.

        Returns:
            The updated `Todo`.

        """
        return self._edit(todo_id, {"archivedTimestamp": None}, action="restore todo")

    def _edit(self, todo_id: int, fields: dict[str, Any], *, action: str) -> Todo:
        """Run `EditTodo` with `fields`, then re-read the to-do.

        Returns:
            The updated `Todo`.

        """
        self._mutate(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, **fields}},
            root_field="EditTodo",
            action=action,
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
        return Todo.model_validate(
            self._one(data, "todo", label="Todo", entity_id=todo_id)
        )

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

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = await self.get_user_id()
        query, variables = self._todo_list_request(
            meeting_id,
            user_id,
            include_completed=include_completed,
            include_archived=include_archived,
        )
        return self._todos_from(await self._execute(query, variables))

    async def create(
        self,
        title: str,
        meeting_id: int | None = None,
        user_id: int | None = None,
        due_date: TimeInput | None = None,
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
        input_ = self._todo_create_input(
            title=title, meeting_id=meeting_id, user_id=user_id, due_date=due_date
        )
        result = await self._mutate(
            self._TODO_CREATE_MUTATION,
            {"input": {**input_, **await self._notes_input(notes)}},
            root_field="CreateTodo",
            action="create todo",
        )
        return Todo.model_validate(result)

    async def update(
        self,
        todo_id: int,
        *,
        title: str | None = None,
        due_date: TimeInput | None = None,
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
        fields = self._todo_edit_fields(title=title, due_date=due_date, user_id=user_id)
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(await self._notes_input(notes))
        return await self._edit(todo_id, fields, action="update todo")

    async def complete(self, todo_id: int) -> Todo:
        """Mark a to-do as complete.

        Args:
            todo_id: The ID of the to-do to complete.

        Returns:
            The updated `Todo`.

        """
        return await self._edit(
            todo_id, {"completedTimestamp": now_timestamp()}, action="complete todo"
        )

    async def reopen(self, todo_id: int) -> Todo:
        """Reopen a completed to-do.

        Args:
            todo_id: The ID of the to-do to reopen.

        Returns:
            The updated `Todo`.

        """
        return await self._edit(
            todo_id, {"completedTimestamp": None}, action="reopen todo"
        )

    async def archive(self, todo_id: int) -> Todo:
        """Archive a to-do.

        Args:
            todo_id: The ID of the to-do to archive.

        Returns:
            The updated `Todo`.

        """
        return await self._edit(
            todo_id, {"archivedTimestamp": now_timestamp()}, action="archive todo"
        )

    async def restore(self, todo_id: int) -> Todo:
        """Restore an archived to-do.

        Args:
            todo_id: The ID of the to-do to restore.

        Returns:
            The updated `Todo`.

        """
        return await self._edit(
            todo_id, {"archivedTimestamp": None}, action="restore todo"
        )

    async def _edit(self, todo_id: int, fields: dict[str, Any], *, action: str) -> Todo:
        """Run `EditTodo` with `fields`, then re-read the to-do.

        Returns:
            The updated `Todo`.

        """
        await self._mutate(
            self._TODO_EDIT_MUTATION,
            {"input": {"todoId": todo_id, **fields}},
            root_field="EditTodo",
            action=action,
        )
        return await self.details(todo_id)
