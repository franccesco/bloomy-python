"""Headline operations for the Bloomy SDK."""

from __future__ import annotations

import builtins

from ..models import (
    HeadlineDetails,
    HeadlineInfo,
    HeadlineListItem,
    OwnerDetails,
)
from ..utils.base_operations import BaseOperations
from .mixins.headlines_transform import HeadlineOperationsMixin


class HeadlineOperations(BaseOperations, HeadlineOperationsMixin):
    """Class to handle all operations related to headlines."""

    def create(
        self,
        meeting_id: int,
        title: str,
        owner_id: int | None = None,
        notes: str | None = None,
    ) -> HeadlineInfo:
        """Create a new headline.

        Args:
            meeting_id: The ID of the meeting
            title: The title of the headline
            owner_id: The ID of the headline owner (default: current user ID)
            notes: Additional notes for the headline

        Returns:
            A HeadlineInfo model instance containing id, title, owner_details,
            and notes_url

        """
        if owner_id is None:
            owner_id = self.user_id

        payload = {"title": title, "ownerId": owner_id}
        if notes is not None:
            payload["notes"] = notes

        response = self._client.post(f"L10/{meeting_id}/headlines", json=payload)
        response.raise_for_status()
        data = response.json()

        return HeadlineInfo(
            id=data["Id"],
            title=data["Name"],
            owner_details=OwnerDetails(id=owner_id, name=None),
            notes_url=data.get("DetailsUrl", ""),
        )

    def update(self, headline_id: int, title: str) -> None:
        """Update a headline.

        Args:
            headline_id: The ID of the headline to update
            title: The new title of the headline

        """
        payload = {"title": title}
        response = self._client.put(f"headline/{headline_id}", json=payload)
        response.raise_for_status()

    def details(self, headline_id: int) -> HeadlineDetails:
        """Get headline details.

        Args:
            headline_id: The ID of the headline

        Returns:
            A HeadlineDetails model instance containing id, title, notes_url,
            meeting_details, owner_details, archived, created_at, and closed_at

        """
        response = self._client.get(
            f"headline/{headline_id}", params={"Include_Origin": "true"}
        )
        response.raise_for_status()
        data = response.json()

        return self._transform_headline_details(data)

    def list(
        self, user_id: int | None = None, meeting_id: int | None = None
    ) -> builtins.list[HeadlineListItem]:
        """Get headlines for a user or a meeting.

        Args:
            user_id: The ID of the user (defaults to initialized user_id)
            meeting_id: The ID of the meeting

        Returns:
            A list of HeadlineListItem model instances containing:
            - id
            - title
            - meeting_details
            - owner_details
            - archived
            - created_at
            - closed_at

        Raises:
            ValueError: If both user_id and meeting_id are provided

        Example:
            ```python
            client.headline.list()
            # Returns: [
            #     HeadlineListItem(
            #         id=1,
            #         title='Headline Title',
            #         meeting_details=MeetingInfo(id=1, title='Team Meeting'),
            #         owner_details=OwnerDetails(id=1, name='John Doe'),
            #         archived=False,
            #         created_at='2023-01-01',
            #         closed_at=None
            #     )
            # ]
            ```

        """
        if user_id and meeting_id:
            raise ValueError("Please provide either user_id or meeting_id, not both.")

        if meeting_id:
            response = self._client.get(f"l10/{meeting_id}/headlines")
        else:
            if user_id is None:
                user_id = self.user_id
            response = self._client.get(f"headline/users/{user_id}")

        response.raise_for_status()
        data = response.json()

        return self._transform_headline_list(data)

    def delete(self, headline_id: int) -> None:
        """Delete a headline.

        Args:
            headline_id: The ID of the headline to delete

        """
        response = self._client.delete(f"headline/{headline_id}")
        response.raise_for_status()
