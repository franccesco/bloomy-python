"""Todo operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from datetime import datetime
from typing import TYPE_CHECKING, TypedDict

from ..utils.base_operations import BaseOperations

if TYPE_CHECKING:
    from typing import Any


class TodoItem(TypedDict):
    """Type definition for todo items."""

    id: int
    title: str
    notes_url: str
    due_date: str | None
    created_at: str
    completed_at: str | None
    status: str


class TodoOperations(BaseOperations):
    """Class to handle all operations related to todos.

    Note:
        This class is already initialized via the client and usable as
        `client.todo.method`
    """

    def list(
        self, user_id: int | None = None, meeting_id: int | None = None
    ) -> builtins.list[TodoItem]:
        """List all todos for a specific user or meeting.

        Args:
            user_id: The ID of the user (default is the initialized user ID)
            meeting_id: The ID of the meeting

        Returns:
            A list of dictionaries containing todo details

        Raises:
            ValueError: If both user_id and meeting_id are provided

        Example:
            >>> # Fetch todos for the current user
            >>> client.todo.list()
            [{"id": 1, "title": "New Todo", "due_date": "2024-06-15", ...}]
        """
        if user_id is not None and meeting_id is not None:
            raise ValueError(
                "Please provide either `user_id` or `meeting_id`, not both."
            )

        if meeting_id is not None:
            response = self._client.get(f"l10/{meeting_id}/todos")
        else:
            if user_id is None:
                user_id = self.user_id
            response = self._client.get(f"todo/user/{user_id}")

        response.raise_for_status()
        data = response.json()

        return [
            {
                "id": todo["Id"],
                "title": todo["Name"],
                "notes_url": todo["DetailsUrl"],
                "due_date": todo["DueDate"],
                "created_at": todo["CreateTime"],
                "completed_at": todo["CompleteTime"],
                "status": "Complete" if todo["Complete"] else "Incomplete",
            }
            for todo in data
        ]

    def create(
        self,
        title: str,
        meeting_id: int,
        due_date: str | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> TodoItem:
        """Create a new todo.

        Args:
            title: The title of the new todo
            meeting_id: The ID of the meeting associated with the todo
            due_date: The due date of the todo (optional)
            user_id: The ID of the user responsible for the todo
                (default: initialized user ID)
            notes: Additional notes for the todo (optional)

        Returns:
            A dictionary containing the newly created todo details

        Example:
            >>> client.todo.create(
                title="New Todo", meeting_id=1, due_date="2024-06-15"
            )
            {"id": 1, "title": "New Todo", "due_date": "2024-06-15", ...}
        """
        if user_id is None:
            user_id = self.user_id

        payload: dict[str, Any] = {
            "title": title,
            "accountableUserId": user_id,
            "notes": notes,
        }

        if due_date is not None:
            payload["dueDate"] = due_date

        response = self._client.post(f"/api/v1/L10/{meeting_id}/todos", json=payload)
        response.raise_for_status()
        data = response.json()

        return {
            "id": data["Id"],
            "title": data["Name"],
            "notes_url": data["DetailsUrl"],
            "due_date": data["DueDate"],
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "status": "Incomplete",
        }

    def complete(self, todo_id: int) -> bool:
        """Mark a todo as complete.

        Args:
            todo_id: The ID of the todo to complete

        Returns:
            True if the operation was successful

        Example:
            >>> client.todo.complete(1)
            True
        """
        response = self._client.post(f"/api/v1/todo/{todo_id}/complete?status=true")
        response.raise_for_status()
        return response.is_success

    def update(
        self,
        todo_id: int,
        title: str | None = None,
        due_date: str | None = None,
    ) -> TodoItem:
        """Update an existing todo.

        Args:
            todo_id: The ID of the todo to update
            title: The new title of the todo (optional)
            due_date: The new due date of the todo (optional)

        Returns:
            A dictionary containing the updated todo details

        Raises:
            ValueError: If no update fields are provided
            RuntimeError: If the update request fails

        Example:
            >>> client.todo.update(
                todo_id=1, title="Updated Todo", due_date="2024-11-01"
            )
            {"id": 1, "title": "Updated Todo", "due_date": "2024-11-01", ...}
        """
        payload: dict[str, Any] = {}

        if title is not None:
            payload["title"] = title

        if due_date is not None:
            payload["dueDate"] = due_date

        if not payload:
            raise ValueError("At least one field must be provided")

        response = self._client.put(f"/api/v1/todo/{todo_id}", json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"Failed to update todo. Status: {response.status_code}")

        return {
            "id": todo_id,
            "title": title or "",
            "notes_url": "",
            "due_date": due_date,
            "created_at": "",
            "completed_at": None,
            "status": "Incomplete",
        }

    def details(self, todo_id: int) -> TodoItem:
        """Retrieve the details of a specific todo item by its ID.

        Args:
            todo_id: The ID of the todo item to retrieve

        Returns:
            A dictionary containing the todo details

        Raises:
            RuntimeError: If the request to retrieve the todo details fails

        Example:
            >>> client.todo.details(1)
            {"id": 1, "title": "Updated Todo", "due_date": "2024-11-01", ...}
        """
        response = self._client.get(f"/api/v1/todo/{todo_id}")

        if not response.is_success:
            raise RuntimeError(
                f"Failed to get todo details. Status: {response.status_code}"
            )

        response.raise_for_status()
        todo = response.json()

        return {
            "id": todo["Id"],
            "title": todo["Name"],
            "notes_url": todo["DetailsUrl"],
            "due_date": todo["DueDate"],
            "created_at": todo["CreateTime"],
            "completed_at": todo["CompleteTime"],
            "status": "Complete" if todo["Complete"] else "Incomplete",
        }
