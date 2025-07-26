"""Meeting operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import Any

from ..exceptions import APIError
from ..models import (
    BulkCreateError,
    BulkCreateResult,
    Issue,
    MeetingAttendee,
    MeetingDetails,
    MeetingListItem,
    ScorecardMetric,
    Todo,
)
from ..utils.base_operations import BaseOperations


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
            A list of MeetingListItem model instances

        Example:
            ```python
            client.meeting.list()
            # Returns: [MeetingListItem(id=123, name="Team Meeting", ...), ...]
            ```

        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(f"L10/{user_id}/list")
        response.raise_for_status()
        data: Any = response.json()

        return [MeetingListItem.model_validate(meeting) for meeting in data]

    def attendees(self, meeting_id: int) -> builtins.list[MeetingAttendee]:
        """List all attendees for a specific meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            A list of MeetingAttendee model instances

        Example:
            ```python
            client.meeting.attendees(1)
            # Returns: [MeetingAttendee(user_id=1, name='John Doe',
            #          image_url='...'), ...]
            ```

        """
        response = self._client.get(f"L10/{meeting_id}/attendees")
        response.raise_for_status()
        data: Any = response.json()

        return [
            MeetingAttendee(
                UserId=attendee["Id"],
                Name=attendee["Name"],
                ImageUrl=attendee.get("ImageUrl", ""),
            )
            for attendee in data
        ]

    def issues(
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
            client.meeting.issues(1)
            # Returns: [Issue(id=1, name='Issue Title',
            #          created_at='2024-06-10', ...), ...]
            ```

        """
        response = self._client.get(
            f"L10/{meeting_id}/issues",
            params={"include_resolved": include_closed},
        )
        response.raise_for_status()
        data: Any = response.json()

        return [
            Issue(
                Id=issue["Id"],
                Name=issue["Name"],
                DetailsUrl=issue["DetailsUrl"],
                CreateDate=issue["CreateTime"],
                ClosedDate=issue["CloseTime"],
                CompletionDate=issue["CloseTime"],
                OwnerId=issue.get("Owner", {}).get("Id", 0),
                OwnerName=issue.get("Owner", {}).get("Name", ""),
                OwnerImageUrl=issue.get("Owner", {}).get("ImageUrl", ""),
                MeetingId=meeting_id,
                MeetingName=issue["Origin"],
            )
            for issue in data
        ]

    def todos(
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
            client.meeting.todos(1)
            # Returns: [Todo(id=1, name='Todo Title', due_date='2024-06-12', ...), ...]
            ```

        """
        response = self._client.get(
            f"L10/{meeting_id}/todos",
            params={"INCLUDE_CLOSED": include_closed},
        )
        response.raise_for_status()
        data: Any = response.json()

        return [Todo.model_validate(todo) for todo in data]

    def metrics(self, meeting_id: int) -> builtins.list[ScorecardMetric]:
        """List all metrics for a specific meeting.

        Args:
            meeting_id: The ID of the meeting

        Returns:
            A list of ScorecardMetric model instances

        Example:
            ```python
            client.meeting.metrics(1)
            # Returns: [ScorecardMetric(id=1, title='Sales', target=100.0,
            #           metric_type='>', unit='currency', ...), ...]
            ```

        """
        response = self._client.get(f"L10/{meeting_id}/measurables")
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

    def details(self, meeting_id: int, include_closed: bool = False) -> MeetingDetails:
        """Retrieve details of a specific meeting.

        Args:
            meeting_id: The ID of the meeting
            include_closed: Whether to include closed issues and todos (default: False)

        Returns:
            A MeetingDetails model instance with comprehensive meeting information

        Raises:
            APIError: If the meeting with the specified ID is not found

        Example:
            ```python
            client.meeting.details(1)
            # Returns: MeetingDetails(id=1, name='Team Meeting', attendees=[...],
            #                        issues=[...], todos=[...], metrics=[...])
            ```

        """
        meetings = self.list()
        meeting = next((m for m in meetings if m.id == meeting_id), None)

        if not meeting:
            raise APIError(f"Meeting with ID {meeting_id} not found", status_code=404)

        return MeetingDetails(
            id=meeting.id,
            name=meeting.name,
            start_date_utc=getattr(meeting, "start_date_utc", None),
            created_date=getattr(meeting, "created_date", None),
            organization_id=getattr(meeting, "organization_id", None),
            attendees=self.attendees(meeting_id),
            issues=self.issues(meeting_id, include_closed=include_closed),
            todos=self.todos(meeting_id, include_closed=include_closed),
            metrics=self.metrics(meeting_id),
        )

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
            ```python
            client.meeting.create("New Meeting", attendees=[2, 3])
            # Returns: {"meeting_id": 1, "title": "New Meeting", "attendees": [2, 3]}
            ```

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
            ```python
            client.meeting.delete(1)
            # Returns: True
            ```

        """
        response = self._client.delete(f"L10/{meeting_id}")
        response.raise_for_status()
        return True

    def create_many(
        self, meetings: builtins.list[dict[str, Any]]
    ) -> BulkCreateResult[dict[str, Any]]:
        """Create multiple meetings in a best-effort manner.

        Processes each meeting sequentially to avoid rate limiting.
        Failed operations are captured and returned alongside successful ones.

        Args:
            meetings: List of dictionaries containing meeting data. Each dict
                should have:
                - title (required): Title of the meeting
                - add_self (optional): Whether to add current user as attendee
                    (default: True)
                - attendees (optional): List of user IDs to add as attendees

        Returns:
            BulkCreateResult containing:
                - successful: List of dicts with meeting_id, title, and attendees
                - failed: List of BulkCreateError instances for failed creations

        Raises:
            ValueError: When required parameters are missing in meeting data

        Example:
            ```python
            result = client.meeting.create_many([
                {"title": "Weekly Team Meeting", "attendees": [2, 3]},
                {"title": "1:1 Meeting", "add_self": False}
            ])

            print(f"Created {len(result.successful)} meetings")
            for error in result.failed:
                print(f"Failed at index {error.index}: {error.error}")
            ```

        """
        successful: builtins.list[dict[str, Any]] = []
        failed: builtins.list[BulkCreateError] = []

        for index, meeting_data in enumerate(meetings):
            try:
                # Extract parameters from the meeting data
                title = meeting_data.get("title")
                add_self = meeting_data.get("add_self", True)
                attendees = meeting_data.get("attendees")

                # Validate required parameters
                if title is None:
                    raise ValueError("title is required")

                # Create the meeting
                created_meeting = self.create(
                    title=title, add_self=add_self, attendees=attendees
                )
                successful.append(created_meeting)

            except Exception as e:
                failed.append(
                    BulkCreateError(index=index, input_data=meeting_data, error=str(e))
                )

        return BulkCreateResult(successful=successful, failed=failed)

    def get_many(self, meeting_ids: list[int]) -> BulkCreateResult[MeetingDetails]:
        """Retrieve details for multiple meetings in a best-effort manner.

        Processes each meeting ID sequentially to avoid rate limiting.
        Failed operations are captured and returned alongside successful ones.

        Args:
            meeting_ids: List of meeting IDs to retrieve details for

        Returns:
            BulkCreateResult containing:
                - successful: List of MeetingDetails instances for successfully
                  retrieved meetings
                - failed: List of BulkCreateError instances for failed retrievals

        Example:
            ```python
            result = client.meeting.get_many([1, 2, 3])

            print(f"Retrieved {len(result.successful)} meetings")
            for error in result.failed:
                print(f"Failed at index {error.index}: {error.error}")
            ```

        """
        successful: builtins.list[MeetingDetails] = []
        failed: builtins.list[BulkCreateError] = []

        for index, meeting_id in enumerate(meeting_ids):
            try:
                # Use the existing details method to get meeting details
                meeting_details = self.details(meeting_id)
                successful.append(meeting_details)

            except Exception as e:
                failed.append(
                    BulkCreateError(
                        index=index, input_data={"meeting_id": meeting_id}, error=str(e)
                    )
                )

        return BulkCreateResult(successful=successful, failed=failed)
