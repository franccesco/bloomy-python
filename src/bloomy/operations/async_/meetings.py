"""Async meeting operations for the Bloomy SDK."""

from __future__ import annotations

import asyncio
import builtins
from typing import TYPE_CHECKING, Any

from ...exceptions import APIError
from ...models import (
    Issue,
    MeetingAttendee,
    MeetingDetails,
    MeetingListItem,
    ScorecardMetric,
    Todo,
)
from ...utils.async_base_operations import AsyncBaseOperations

if TYPE_CHECKING:
    import httpx


class AsyncMeetingOperations(AsyncBaseOperations):
    """Async class to handle all operations related to meetings.

    Note:
        This class is already initialized via the client and usable as
        `client.meeting.method`
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Initialize the async meeting operations.

        Args:
            client: The async HTTP client to use for API requests.
        """
        super().__init__(client)

    async def list(self, user_id: int | None = None) -> builtins.list[MeetingListItem]:
        """List all meetings for a specific user.

        Args:
            user_id: The ID of the user (default is the initialized user ID)

        Returns:
            A list of MeetingListItem model instances

        Example:
            ```python
            await client.meeting.list()
            # Returns: [MeetingListItem(id=123, name="Team Meeting", ...), ...]
            ```
        """
        if user_id is None:
            user_id = await self.get_user_id()

        response = await self._client.get(f"L10/{user_id}/list")
        response.raise_for_status()
        data: Any = response.json()

        return [MeetingListItem.model_validate(meeting) for meeting in data]

    async def attendees(self, meeting_id: int) -> builtins.list[MeetingAttendee]:
        """List all attendees for a specific meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            A list of MeetingAttendee model instances

        Example:
            ```python
            await client.meeting.attendees(1)
            # Returns: [MeetingAttendee(user_id=1, name='John Doe',
            #          image_url='...'), ...]
            ```
        """
        response = await self._client.get(f"L10/{meeting_id}/attendees")
        response.raise_for_status()
        data: Any = response.json()

        return [MeetingAttendee.model_validate(attendee) for attendee in data]

    async def issues(
        self, meeting_id: int, include_closed: bool = False
    ) -> builtins.list[Issue]:
        """List all issues for a specific meeting.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed issues (default: False)

        Returns:
            A list of Issue model instances

        Example:
            ```python
            await client.meeting.issues(1)
            # Returns: [Issue(id=1, name='Issue Title',
            #          created_at='2024-06-10', ...), ...]
            ```
        """
        response = await self._client.get(
            f"L10/{meeting_id}/issues",
            params={"include_resolved": include_closed},
        )
        response.raise_for_status()
        data: Any = response.json()

        return [Issue.model_validate(issue) for issue in data]

    async def todos(
        self, meeting_id: int, include_closed: bool = False
    ) -> builtins.list[Todo]:
        """List all todos for a specific meeting.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed todos (default: False)

        Returns:
            A list of Todo model instances

        Example:
            ```python
            await client.meeting.todos(1)
            # Returns: [Todo(id=1, name='Todo Title', due_date='2024-06-12', ...), ...]
            ```
        """
        response = await self._client.get(
            f"L10/{meeting_id}/todos",
            params={"INCLUDE_CLOSED": include_closed},
        )
        response.raise_for_status()
        data: Any = response.json()

        return [Todo.model_validate(todo) for todo in data]

    async def metrics(self, meeting_id: int) -> builtins.list[ScorecardMetric]:
        """List all metrics for a specific meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            A list of ScorecardMetric model instances

        Example:
            ```python
            await client.meeting.metrics(1)
            # Returns: [ScorecardMetric(id=1, title='Sales', target=100.0,
            #           metric_type='>', unit='currency', ...), ...]
            ```
        """
        response = await self._client.get(f"L10/{meeting_id}/measurables")
        response.raise_for_status()
        raw_data = response.json()

        if not isinstance(raw_data, list):
            return []

        metrics: list[ScorecardMetric] = []
        # Type the list explicitly
        data_list: list[Any] = raw_data  # type: ignore[assignment]
        for item in data_list:
            if not isinstance(item, dict):
                continue

            # Cast to Any dict to satisfy type checker
            item_dict: dict[str, Any] = item  # type: ignore[assignment]
            measurable_id = item_dict.get("Id")
            measurable_name = item_dict.get("Name")

            if not measurable_id or not measurable_name:
                continue

            owner_data = item_dict.get("Owner", {})
            if not isinstance(owner_data, dict):
                owner_data = {}
            owner_dict: dict[str, Any] = owner_data  # type: ignore[assignment]

            metrics.append(
                ScorecardMetric(
                    Id=int(measurable_id),
                    Title=str(measurable_name).strip(),
                    Target=float(item_dict.get("Target", 0)),
                    Unit=str(item_dict.get("Modifiers", "")),
                    WeekNumber=0,  # Not provided in this endpoint
                    Value=None,
                    MetricType=str(item_dict.get("Direction", "")),
                    AccountableUserId=int(owner_dict.get("Id") or 0),
                    AccountableUserName=str(owner_dict.get("Name") or ""),
                    IsInverse=False,
                )
            )

        return metrics

    async def details(
        self, meeting_id: int, include_closed: bool = False
    ) -> MeetingDetails:
        """Retrieve details of a specific meeting.

        This method optimizes performance by making parallel API calls to fetch
        attendees, issues, todos, and metrics concurrently.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed issues and todos (default: False)

        Returns:
            A MeetingDetails model instance with comprehensive meeting information

        Example:
            ```python
            await client.meeting.details(1)
            # Returns: MeetingDetails(id=1, name='Team Meeting', attendees=[...],
            #                        issues=[...], todos=[...], metrics=[...])
            ```
        """
        meetings = await self.list()
        meeting = next((m for m in meetings if m.id == meeting_id), None)

        if not meeting:
            raise APIError(f"Meeting with ID {meeting_id} not found", status_code=404)

        # Fetch all sub-resources in parallel for better performance
        attendees_task = asyncio.create_task(self.attendees(meeting_id))
        issues_task = asyncio.create_task(
            self.issues(meeting_id, include_closed=include_closed)
        )
        todos_task = asyncio.create_task(
            self.todos(meeting_id, include_closed=include_closed)
        )
        metrics_task = asyncio.create_task(self.metrics(meeting_id))

        # Wait for all tasks to complete
        attendees, issues, todos, metrics = await asyncio.gather(
            attendees_task, issues_task, todos_task, metrics_task
        )

        return MeetingDetails(
            id=meeting.id,
            name=meeting.name,
            start_date_utc=getattr(meeting, "start_date_utc", None),
            created_date=getattr(meeting, "created_date", None),
            organization_id=getattr(meeting, "organization_id", None),
            attendees=attendees,
            issues=issues,
            todos=todos,
            metrics=metrics,
        )

    async def create(
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
            ```python
            await client.meeting.create("New Meeting", attendees=[2, 3])
            # Returns: {"meeting_id": 1, "title": "New Meeting", "attendees": [2, 3]}
            ```
        """
        if attendees is None:
            attendees = []

        payload = {"title": title, "addSelf": add_self}
        response = await self._client.post("L10/create", json=payload)
        response.raise_for_status()
        data: Any = response.json()

        meeting_id = data["meetingId"]

        # Add attendees in parallel for better performance
        if attendees:
            tasks = [
                self._client.post(f"L10/{meeting_id}/attendees/{attendee_id}")
                for attendee_id in attendees
            ]
            responses = await asyncio.gather(*tasks)
            for response in responses:
                response.raise_for_status()

        return {"meeting_id": meeting_id, "title": title, "attendees": attendees}

    async def delete(self, meeting_id: int) -> bool:
        """Delete a meeting.

        Args:
            meeting_id: The ID of the meeting to delete

        Returns:
            True if deletion was successful

        Example:
            ```python
            await client.meeting.delete(1)
            # Returns: True
            ```
        """
        response = await self._client.delete(f"L10/{meeting_id}")
        response.raise_for_status()
        return True
