"""Async issue operations for the Bloomy SDK."""

from __future__ import annotations

import asyncio
import builtins
from typing import TYPE_CHECKING

from ...models import (
    BulkCreateError,
    BulkCreateResult,
    CreatedIssue,
    IssueDetails,
    IssueListItem,
)
from ...utils.async_base_operations import AsyncBaseOperations

if TYPE_CHECKING:
    from typing import Any

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
        # Create a semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def create_single_issue(
            index: int, issue_data: dict[str, Any]
        ) -> tuple[int, CreatedIssue | BulkCreateError]:
            """Create a single issue with error handling.

            Returns:
                Tuple of (index, result) where result is either CreatedIssue
                or BulkCreateError.

            Raises:
                ValueError: When required parameters are missing.

            """
            async with semaphore:
                try:
                    # Extract parameters from the issue data
                    meeting_id = issue_data.get("meeting_id")
                    title = issue_data.get("title")
                    user_id = issue_data.get("user_id")
                    notes = issue_data.get("notes")

                    # Validate required parameters
                    if meeting_id is None:
                        raise ValueError("meeting_id is required")
                    if title is None:
                        raise ValueError("title is required")

                    # Create the issue
                    created_issue = await self.create(
                        meeting_id=meeting_id, title=title, user_id=user_id, notes=notes
                    )
                    return (index, created_issue)

                except Exception as e:
                    error = BulkCreateError(
                        index=index, input_data=issue_data, error=str(e)
                    )
                    return (index, error)

        # Create tasks for all issues
        tasks = [
            create_single_issue(index, issue_data)
            for index, issue_data in enumerate(issues)
        ]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)

        # Sort results to maintain order
        results.sort(key=lambda x: x[0])

        # Separate successful and failed results
        successful: builtins.list[CreatedIssue] = []
        failed: builtins.list[BulkCreateError] = []

        for _, result in results:
            if isinstance(result, CreatedIssue):
                successful.append(result)
            else:
                failed.append(result)

        return BulkCreateResult(successful=successful, failed=failed)
