"""Meeting operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import AsyncGraphQLOperations, GraphQLOperations, dig_nodes
from ..models import Meeting, MeetingListItem, User


class MeetingOperationsMixin:
    """Shared GraphQL documents and response transforms for meeting operations."""

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

    _ATTENDEE_FIELDS = "id firstName lastName fullName avatar user { email }"

    _MEETING_DETAILS_QUERY = f"""
    query($id: Long!) {{
      meeting(id: $id) {{
        id
        name
        orgId
        meetingType
        createdTimestamp
        archived
        attendees(order: [{{ fullName: ASC }}]) {{
          nodes {{
            {_ATTENDEE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _MEETING_ATTENDEES_QUERY = f"""
    query($id: Long!) {{
      meeting(id: $id) {{
        attendees(order: [{{ fullName: ASC }}]) {{
          nodes {{
            {_ATTENDEE_FIELDS}
          }}
        }}
      }}
    }}
    """

    def _transform_attendee(self, node: dict[str, Any]) -> User:
        """Transform a raw `attendees` connection node into a `User` model.

        Returns:
            A `User` model instance.

        """
        user_ref: dict[str, Any] = node.get("user") or {}
        # Constructed with alias keyword names (matching the raw GraphQL
        # field names) rather than the model's snake_case field names: the
        # model declares `Field(alias=...)` for these, and that alias is
        # what pydantic's generated `__init__` exposes to static type
        # checkers even though `validate_by_name=True` also accepts the
        # field name at runtime.
        return User(
            id=node["id"],
            firstName=node.get("firstName"),
            lastName=node.get("lastName"),
            fullName=node.get("fullName"),
            avatar=node.get("avatar"),
            email=user_ref.get("email"),
        )

    def _transform_meeting_list_item(self, node: dict[str, Any]) -> MeetingListItem:
        """Transform a raw `meetingsListLookup` node into a `MeetingListItem`.

        Returns:
            A `MeetingListItem` model instance.

        """
        return MeetingListItem(**node)

    def _transform_meeting(self, data: dict[str, Any]) -> Meeting:
        """Transform a raw `meeting(id)` response into a `Meeting` model.

        Returns:
            A `Meeting` model instance.

        """
        attendee_nodes = dig_nodes(data, "attendees")
        return Meeting(
            id=data["id"],
            name=data.get("name"),
            orgId=data.get("orgId"),
            meetingType=data.get("meetingType"),
            createdTimestamp=data["createdTimestamp"],
            archived=data.get("archived", False),
            attendees=[self._transform_attendee(node) for node in attendee_nodes],
        )


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
        nodes = dig_nodes(data, "user", "meetingsListLookup")
        return [self._transform_meeting_list_item(node) for node in nodes]

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
        return self._transform_meeting(
            self._require_entity(data, "meeting", meeting_id, "Meeting")
        )

    def attendees(self, meeting_id: int) -> builtins.list[User]:
        """List the attendees of a meeting.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A list of `User` model instances, ordered by full name.

        """
        data = self._execute(self._MEETING_ATTENDEES_QUERY, {"id": meeting_id})
        nodes = dig_nodes(data, "meeting", "attendees")
        return [self._transform_attendee(node) for node in nodes]


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
        nodes = dig_nodes(data, "user", "meetingsListLookup")
        return [self._transform_meeting_list_item(node) for node in nodes]

    async def details(self, meeting_id: int) -> Meeting:
        """Get details for a meeting, including its attendees.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A `Meeting` model instance.

        """
        data = await self._execute(self._MEETING_DETAILS_QUERY, {"id": meeting_id})
        return self._transform_meeting(
            self._require_entity(data, "meeting", meeting_id, "Meeting")
        )

    async def attendees(self, meeting_id: int) -> builtins.list[User]:
        """List the attendees of a meeting.

        Args:
            meeting_id: The ID of the meeting.

        Returns:
            A list of `User` model instances, ordered by full name.

        """
        data = await self._execute(self._MEETING_ATTENDEES_QUERY, {"id": meeting_id})
        nodes = dig_nodes(data, "meeting", "attendees")
        return [self._transform_attendee(node) for node in nodes]
