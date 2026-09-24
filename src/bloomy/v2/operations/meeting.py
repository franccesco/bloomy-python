"""Meeting operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins

from ..base import AsyncGraphQLOperations, GraphQLOperations, dig_nodes
from ..models import Meeting, MeetingListItem, User

_ATTENDEES_FIELD = """
attendees(order: [{ fullName: ASC }]) {
  nodes {
    id
    firstName
    lastName
    fullName
    avatar
    user { email }
  }
}
"""


class MeetingOperationsMixin:
    """GraphQL documents shared by meeting operations."""

    # `user(id){ meetingsListLookup }` is used instead of the root `meetings`
    # field, which is expensive and can trip the server's execution timeout.
    _MEETING_LIST_QUERY = """
    query($userId: Long!) {
      user(id: $userId) {
        meetingsListLookup(
          where: { and: [{ userIsAttendee: { eq: true } }] }
          order: [{ name: ASC }]
        ) {
          nodes {
            id
            name
            meetingType
            createdTimestamp
            archived
            userIsAttendee
            isCurrentUserAdmin
          }
        }
      }
    }
    """

    _MEETING_DETAILS_QUERY = f"""
    query($id: Long!) {{
      meeting(id: $id) {{
        id
        name
        orgId
        meetingType
        createdTimestamp
        archived
        {_ATTENDEES_FIELD}
      }}
    }}
    """

    _MEETING_ATTENDEES_QUERY = f"""
    query($id: Long!) {{
      meeting(id: $id) {{
        {_ATTENDEES_FIELD}
      }}
    }}
    """


class MeetingOperations(GraphQLOperations, MeetingOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to meetings."""

    def list(self, user_id: int | None = None) -> builtins.list[MeetingListItem]:
        """List meetings a user attends.

        Args:
            user_id: The ID of the user (defaults to the current user).

        Returns:
            A list of `MeetingListItem` model instances, ordered by name.

        Example:
            ```python
            client.v2.meeting.list()
            # Returns: [MeetingListItem(id=1, name='L10', ...), ...]
            ```

        """
        if user_id is None:
            user_id = self.user_id
        data = self._execute(self._MEETING_LIST_QUERY, {"userId": user_id})
        return [
            MeetingListItem.model_validate(node)
            for node in dig_nodes(data, "user", "meetingsListLookup")
        ]

    def details(self, meeting_id: int) -> Meeting:
        """Get details for a meeting, including its attendees.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A `Meeting` model instance.

        Example:
            ```python
            client.v2.meeting.details(349524)
            # Returns: Meeting(id=349524, name='v2 API', ...)
            ```

        """
        data = self._execute(self._MEETING_DETAILS_QUERY, {"id": meeting_id})
        return Meeting.model_validate(
            self._one(data, "meeting", label="Meeting", entity_id=meeting_id)
        )

    def attendees(self, meeting_id: int) -> builtins.list[User]:
        """List the attendees of a meeting.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A list of `User` model instances, ordered by full name.

        """
        data = self._execute(self._MEETING_ATTENDEES_QUERY, {"id": meeting_id})
        return [
            User.model_validate(node)
            for node in dig_nodes(data, "meeting", "attendees")
        ]


class AsyncMeetingOperations(AsyncGraphQLOperations, MeetingOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to meetings."""

    async def list(self, user_id: int | None = None) -> builtins.list[MeetingListItem]:
        """List meetings a user attends.

        Args:
            user_id: The ID of the user (defaults to the current user).

        Returns:
            A list of `MeetingListItem` model instances, ordered by name.

        """
        if user_id is None:
            user_id = await self.get_user_id()
        data = await self._execute(self._MEETING_LIST_QUERY, {"userId": user_id})
        return [
            MeetingListItem.model_validate(node)
            for node in dig_nodes(data, "user", "meetingsListLookup")
        ]

    async def details(self, meeting_id: int) -> Meeting:
        """Get details for a meeting, including its attendees.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A `Meeting` model instance.

        """
        data = await self._execute(self._MEETING_DETAILS_QUERY, {"id": meeting_id})
        return Meeting.model_validate(
            self._one(data, "meeting", label="Meeting", entity_id=meeting_id)
        )

    async def attendees(self, meeting_id: int) -> builtins.list[User]:
        """List the attendees of a meeting.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A list of `User` model instances, ordered by full name.

        """
        data = await self._execute(self._MEETING_ATTENDEES_QUERY, {"id": meeting_id})
        return [
            User.model_validate(node)
            for node in dig_nodes(data, "meeting", "attendees")
        ]
