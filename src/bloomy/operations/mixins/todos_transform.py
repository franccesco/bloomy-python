"""Mixin for shared todo operations logic."""

from __future__ import annotations

from typing import Any


class TodoOperationsMixin:
    """Shared logic for todo operations."""

    def _build_meeting_todo_payload(
        self,
        title: str,
        user_id: int,
        notes: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Build payload for creating a meeting todo.

        Args:
            title: The title of the todo.
            user_id: The ID of the user responsible for the todo.
            notes: Additional notes for the todo.
            due_date: The due date of the todo.

        Returns:
            A dictionary containing the meeting todo payload.

        """
        payload: dict[str, Any] = {
            "Title": title,
            "ForId": user_id,
        }
        if notes is not None:
            payload["Notes"] = notes
        if due_date is not None:
            payload["dueDate"] = due_date

        return payload

    def _build_user_todo_payload(
        self,
        title: str,
        user_id: int,
        notes: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """Build payload for creating a user todo.

        Args:
            title: The title of the todo.
            user_id: The ID of the user responsible for the todo.
            notes: Additional notes for the todo.
            due_date: The due date of the todo.

        Returns:
            A dictionary containing the user todo payload.

        """
        payload: dict[str, Any] = {
            "title": title,
            "accountableUserId": user_id,
        }

        if notes is not None:
            payload["notes"] = notes

        if due_date is not None:
            payload["dueDate"] = due_date

        return payload
