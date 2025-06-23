"""Async issue operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from ...models import CreatedIssue, IssueDetails, IssueListItem
from ...utils.async_base_operations import AsyncBaseOperations

if TYPE_CHECKING:
    import httpx


class AsyncIssueOperations(AsyncBaseOperations):
    """Async class to handle all operations related to issues."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Initialize the async issue operations.

        Args:
            client: The async HTTP client to use for API requests.

        """
        super().__init__(client)

    async def details(self, issue_id: int) -> IssueDetails:
        """Retrieve detailed information about a specific issue.

        Args:
            issue_id: Unique identifier of the issue

        Returns:
            An IssueDetails model instance containing detailed information
            about the issue

        """
        response = await self._client.get(f"issues/{issue_id}")
        response.raise_for_status()
        data = response.json()

        return IssueDetails(
            id=data["Id"],
            title=data["Name"],
            notes_url=data["DetailsUrl"],
            created_at=data["CreateTime"],
            completed_at=data["CloseTime"],
            meeting_id=data["OriginId"],
            meeting_title=data["Origin"],
            user_id=data["Owner"]["Id"],
            user_name=data["Owner"]["Name"],
        )

    async def list(
        self, user_id: int | None = None, meeting_id: int | None = None
    ) -> builtins.list[IssueListItem]:
        """List issues filtered by user or meeting.

        Args:
            user_id: Unique identifier of the user (optional)
            meeting_id: Unique identifier of the meeting (optional)

        Returns:
            A list of IssueListItem model instances matching the filter criteria

        Raises:
            ValueError: When both user_id and meeting_id are provided

        """
        if user_id and meeting_id:
            raise ValueError(
                "Please provide either `user_id` or `meeting_id`, not both."
            )

        if meeting_id:
            response = await self._client.get(f"l10/{meeting_id}/issues")
        else:
            if user_id is None:
                user_id = await self.get_user_id()
            response = await self._client.get(f"issues/users/{user_id}")

        response.raise_for_status()
        data = response.json()

        return [
            IssueListItem(
                id=issue["Id"],
                title=issue["Name"],
                notes_url=issue["DetailsUrl"],
                created_at=issue["CreateTime"],
                meeting_id=issue["OriginId"],
                meeting_title=issue["Origin"],
            )
            for issue in data
        ]

    async def solve(self, issue_id: int) -> bool:
        """Mark an issue as completed/solved.

        Args:
            issue_id: Unique identifier of the issue to be solved

        Returns:
            True if issue was successfully solved

        """
        response = await self._client.post(
            f"issues/{issue_id}/complete", json={"complete": True}
        )
        response.raise_for_status()
        return True

    async def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> CreatedIssue:
        """Create a new issue in the system.

        Args:
            meeting_id: Unique identifier of the associated meeting
            title: Title/name of the issue
            user_id: Unique identifier of the issue owner (defaults to current user)
            notes: Additional notes or description for the issue (optional)

        Returns:
            A CreatedIssue model instance containing the newly created issue details

        """
        if user_id is None:
            user_id = await self.get_user_id()

        payload = {
            "title": title,
            "meetingid": meeting_id,
            "ownerid": user_id,
        }

        if notes is not None:
            payload["notes"] = notes

        response = await self._client.post("issues/create", json=payload)
        response.raise_for_status()
        data = response.json()

        return CreatedIssue(
            id=data["Id"],
            meeting_id=data["OriginId"],
            meeting_title=data["Origin"],
            title=data["Name"],
            user_id=data["Owner"]["Id"],
            notes_url=data["DetailsUrl"],
        )
