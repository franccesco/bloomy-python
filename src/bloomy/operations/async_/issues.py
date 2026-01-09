"""Async issue operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from ...models import (
    BulkCreateResult,
    CreatedIssue,
    IssueDetails,
    IssueListItem,
)
from ...utils.async_base_operations import AsyncBaseOperations
from ..mixins.issues_transform import IssueOperationsMixin

if TYPE_CHECKING:
    from typing import Any


class AsyncIssueOperations(AsyncBaseOperations, IssueOperationsMixin):
    """Async class to handle all operations related to issues."""

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

        return self._transform_issue_details(data)

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

        return self._transform_issue_list(data)

    async def complete(self, issue_id: int) -> IssueDetails:
        """Mark an issue as completed/solved.

        Args:
            issue_id: Unique identifier of the issue to be completed

        Returns:
            The updated IssueDetails

        Example:
            ```python
            completed_issue = await client.issue.complete(123)
            print(completed_issue.completed_at)
            ```

        """
        response = await self._client.post(
            f"issues/{issue_id}/complete", json={"complete": True}
        )
        response.raise_for_status()
        return await self.details(issue_id)

    async def update(
        self,
        issue_id: int,
        title: str | None = None,
        notes: str | None = None,
    ) -> IssueDetails:
        """Update an existing issue.

        Args:
            issue_id: The ID of the issue to update
            title: New title for the issue (optional)
            notes: New notes for the issue (optional)

        Returns:
            The updated IssueDetails

        Raises:
            ValueError: If no update fields are provided

        Example:
            ```python
            updated = await client.issue.update(123, title="New Title")
            print(updated.title)
            ```

        """
        if title is None and notes is None:
            raise ValueError(
                "At least one field (title or notes) must be provided for update"
            )

        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if notes is not None:
            payload["notes"] = notes

        response = await self._client.put(f"issues/{issue_id}", json=payload)
        response.raise_for_status()

        return await self.details(issue_id)

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

        return self._transform_created_issue(data)

    async def create_many(
        self, issues: builtins.list[dict[str, Any]], max_concurrent: int = 5
    ) -> BulkCreateResult[CreatedIssue]:
        """Create multiple issues concurrently in a best-effort manner.

        Uses asyncio to process multiple issue creations concurrently with rate
        limiting.
        Failed operations are captured and returned alongside successful ones.

        Args:
            issues: List of dictionaries containing issue data. Each dict should have:
                - meeting_id (required): ID of the associated meeting
                - title (required): Title of the issue
                - user_id (optional): ID of the issue owner (defaults to current user)
                - notes (optional): Additional notes for the issue
            max_concurrent: Maximum number of concurrent requests (default: 5)

        Returns:
            BulkCreateResult containing:
                - successful: List of CreatedIssue instances for successful creations
                - failed: List of BulkCreateError instances for failed creations


        Example:
            ```python
            result = await client.issue.create_many([
                {"meeting_id": 123, "title": "Issue 1", "notes": "Details"},
                {"meeting_id": 123, "title": "Issue 2", "user_id": 456}
            ])

            print(f"Created {len(result.successful)} issues")
            for error in result.failed:
                print(f"Failed at index {error.index}: {error.error}")
            ```

        """

        async def _create_single(data: dict[str, Any]) -> CreatedIssue:
            return await self.create(
                meeting_id=data["meeting_id"],
                title=data["title"],
                user_id=data.get("user_id"),
                notes=data.get("notes"),
            )

        return await self._process_bulk_async(
            issues,
            _create_single,
            required_fields=["meeting_id", "title"],
            max_concurrent=max_concurrent,
        )
