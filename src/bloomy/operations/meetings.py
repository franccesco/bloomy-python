"""Meeting operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING, Any, TypedDict

from ..utils.base_operations import BaseOperations

if TYPE_CHECKING:
    pass


class MeetingListItem(TypedDict):
    """Type definition for meeting list items."""

    id: int
    title: str


class AttendeeInfo(TypedDict):
    """Type definition for attendee information."""

    id: int
    name: str


class IssueInfo(TypedDict):
    """Type definition for issue information."""

    id: int
    title: str
    notes_url: str
    created_at: str
    completed_at: str | None
    user_id: int
    user_name: str
    meeting_id: int
    meeting_title: str


class TodoInfo(TypedDict):
    """Type definition for todo information."""

    id: int
    title: str
    due_date: str
    notes_url: str
    status: str
    created_at: str
    completed_at: str | None
    user_id: int
    user_name: str


class MetricInfo(TypedDict):
    """Type definition for metric information."""

    id: int
    title: str
    target: float
    operator: str
    format: str
    user_id: int | None
    user_name: str | None
    admin_id: int | None
    admin_name: str | None


class MeetingDetails(TypedDict):
    """Type definition for meeting details."""

    id: int
    title: str
    attendees: list[AttendeeInfo]
    issues: list[IssueInfo]
    todos: list[TodoInfo]
    metrics: list[MetricInfo]


class MeetingOperations(BaseOperations):
    """Class to handle all operations related to meetings.

    Note:
        This class is already initialized via the client and usable as
        `client.meeting.method`
    """

    def list(self, user_id: int | None = None) -> builtins.list[MeetingListItem]:
        """List all meetings for a specific user.

        Args:
            user_id: The ID of the user (default is the initialized user ID)

        Returns:
            A list of dictionaries containing meeting details

        Example:
            >>> client.meeting.list()
            [{"id": 123, "title": "Team Meeting"}, ...]
        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(f"L10/{user_id}/list")
        response.raise_for_status()
        data: Any = response.json()

        return [{"id": meeting["Id"], "title": meeting["Name"]} for meeting in data]

    def attendees(self, meeting_id: int) -> builtins.list[AttendeeInfo]:
        """List all attendees for a specific meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            A list of dictionaries containing attendee details

        Example:
            >>> client.meeting.attendees(1)
            [{"name": "John Doe", "id": 1}, ...]
        """
        response = self._client.get(f"L10/{meeting_id}/attendees")
        response.raise_for_status()
        data: Any = response.json()

        return [{"id": attendee["Id"], "name": attendee["Name"]} for attendee in data]

    def issues(
        self, meeting_id: int, include_closed: bool = False
    ) -> builtins.list[IssueInfo]:
        """List all issues for a specific meeting.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed issues (default: False)

        Returns:
            A list of dictionaries containing issue details

        Example:
            >>> client.meeting.issues(1)
            [{"id": 1, "title": "Issue Title", "created_at": "2024-06-10", ...}, ...]
        """
        response = self._client.get(
            f"L10/{meeting_id}/issues",
            params={"include_resolved": include_closed},
        )
        response.raise_for_status()
        data: Any = response.json()

        return [
            {
                "id": issue["Id"],
                "title": issue["Name"],
                "notes_url": issue["DetailsUrl"],
                "created_at": issue["CreateTime"],
                "completed_at": issue["CloseTime"],
                "user_id": issue.get("Owner", {}).get("Id"),
                "user_name": issue.get("Owner", {}).get("Name"),
                "meeting_id": meeting_id,
                "meeting_title": issue["Origin"],
            }
            for issue in data
        ]

    def todos(
        self, meeting_id: int, include_closed: bool = False
    ) -> builtins.list[TodoInfo]:
        """List all todos for a specific meeting.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed todos (default: False)

        Returns:
            A list of dictionaries containing todo details

        Example:
            >>> client.meeting.todos(1)
            [{"id": 1, "title": "Todo Title", "due_date": "2024-06-12", ...}, ...]
        """
        response = self._client.get(
            f"L10/{meeting_id}/todos",
            params={"INCLUDE_CLOSED": include_closed},
        )
        response.raise_for_status()
        data: Any = response.json()

        return [
            {
                "id": todo["Id"],
                "title": todo["Name"],
                "due_date": todo["DueDate"],
                "notes_url": todo["DetailsUrl"],
                "status": "Complete" if todo["Complete"] else "Incomplete",
                "created_at": todo["CreateTime"],
                "completed_at": todo["CompleteTime"],
                "user_id": todo.get("Owner", {}).get("Id"),
                "user_name": todo.get("Owner", {}).get("Name"),
            }
            for todo in data
        ]

    def metrics(self, meeting_id: int) -> builtins.list[MetricInfo]:
        """List all metrics for a specific meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            A list of dictionaries containing metric details

        Example:
            >>> client.meeting.metrics(1)
            [{"id": 1, "name": "Sales", "target": 100, "operator": ">",
             "format": "currency", ...}, ...]
        """
        response = self._client.get(f"L10/{meeting_id}/measurables")
        response.raise_for_status()
        data: Any = response.json()

        if not isinstance(data, list):
            return []

        metrics: list[MetricInfo] = []
        for measurable in data:  # type: ignore[assignment]
            if not measurable.get("Id") or not measurable.get("Name"):
                continue

            metrics.append(
                {
                    "id": measurable["Id"],
                    "title": measurable["Name"].strip(),
                    "target": float(measurable.get("Target", 0)),
                    "operator": str(measurable.get("Direction", "")),
                    "format": str(measurable.get("Modifiers", "")),
                    "user_id": measurable.get("Owner", {}).get("Id"),
                    "user_name": measurable.get("Owner", {}).get("Name"),
                    "admin_id": measurable.get("Admin", {}).get("Id"),
                    "admin_name": measurable.get("Admin", {}).get("Name"),
                }
            )

        return metrics

    def details(self, meeting_id: int, include_closed: bool = False) -> MeetingDetails:
        """Retrieve details of a specific meeting.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed issues and todos (default: False)

        Returns:
            A dictionary containing detailed information about the meeting

        Example:
            >>> client.meeting.details(1)
            {"id": 1, "name": "Team Meeting", "attendees": [...],
             "issues": [...], "todos": [...], "metrics": [...]}
        """
        meetings = self.list()
        meeting = next((m for m in meetings if m["id"] == meeting_id), None)

        if not meeting:
            raise ValueError(f"Meeting with ID {meeting_id} not found")

        return {
            "id": meeting["id"],
            "title": meeting["title"],
            "attendees": self.attendees(meeting_id),
            "issues": self.issues(meeting_id, include_closed=include_closed),
            "todos": self.todos(meeting_id, include_closed=include_closed),
            "metrics": self.metrics(meeting_id),
        }

    def create(
        self,
        title: str,
        add_self: bool = True,
        attendees: builtins.list[int] | None = None,
    ) -> dict[str, Any]:
        """Create a new meeting.

        Args:
            title: The title of the new meeting
            add_self: Whether to add the current user as an attendee (default: True)
            attendees: A list of user IDs to add as attendees

        Returns:
            A dictionary containing meeting_id, title and attendees array

        Example:
            >>> client.meeting.create("New Meeting", attendees=[2, 3])
            {"meeting_id": 1, "title": "New Meeting", "attendees": [2, 3]}
        """
        if attendees is None:
            attendees = []

        payload = {"title": title, "addSelf": add_self}
        response = self._client.post("L10/create", json=payload)
        response.raise_for_status()
        data: Any = response.json()

        meeting_id = data["meetingId"]

        # Add attendees
        for attendee_id in attendees:
            attendee_response = self._client.post(
                f"L10/{meeting_id}/attendees/{attendee_id}"
            )
            attendee_response.raise_for_status()

        return {"meeting_id": meeting_id, "title": title, "attendees": attendees}

    def delete(self, meeting_id: int) -> bool:
        """Delete a meeting.

        Args:
            meeting_id: The ID of the meeting to delete

        Returns:
            True if deletion was successful

        Example:
            >>> client.meeting.delete(1)
            True
        """
        response = self._client.delete(f"L10/{meeting_id}")
        response.raise_for_status()
        return True
