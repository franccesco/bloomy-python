"""Headline operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import (
    MEETING_REF_FIELDS,
    NOTES_FIELDS,
    USER_REF_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    compact,
    dig_nodes,
    merge_nodes,
)
from ..models import Headline

_HEADLINE_FIELDS = f"""
id
title
recurrenceId
archived
archivedTimestamp
dateCreated
{NOTES_FIELDS}
{USER_REF_FIELDS}
{MEETING_REF_FIELDS}
"""


class HeadlineOperationsMixin:
    """GraphQL documents, inputs, and response parsing shared by headline operations."""

    _HEADLINE_DETAILS_QUERY = f"""
    query($id: Long!) {{
      headline(id: $id) {{
        {_HEADLINE_FIELDS}
      }}
    }}
    """

    # `meeting.headlines` holds only open headlines; archived ones are in the
    # separate `archivedHeadlines` connection.
    _HEADLINE_MEETING_LIST_QUERY = f"""
    query($meetingId: Long!, $includeArchived: Boolean!) {{
      meeting(id: $meetingId) {{
        headlines(order: [{{ dateCreated: ASC }}]) {{
          nodes {{
            {_HEADLINE_FIELDS}
          }}
        }}
        archivedHeadlines(order: [{{ dateCreated: ASC }}])
          @include(if: $includeArchived) {{
          nodes {{
            {_HEADLINE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _HEADLINE_USER_LIST_QUERY = f"""
    query($userId: Long!, $where: HeadlineQueryModelFilterInput) {{
      headlines(userId: $userId, where: $where, order: [{{ dateCreated: ASC }}]) {{
        nodes {{
          {_HEADLINE_FIELDS}
        }}
      }}
    }}
    """

    _HEADLINE_CREATE_MUTATION = """
    mutation($input: HeadlineCreateModelInput!) {
      CreateHeadline(input: $input) {
        id
      }
    }
    """

    _HEADLINE_EDIT_MUTATION = """
    mutation($input: HeadlineEditModelInput!) {
      EditHeadline(input: $input) {
        id
      }
    }
    """

    @classmethod
    def _headline_list_request(
        cls, meeting_id: int | None, user_id: int | None, *, include_archived: bool
    ) -> tuple[str, dict[str, Any]]:
        """Pick the list document for a meeting or a user, with its variables.

        Root `headlines(userId)` includes archived headlines, so the user
        variant filters them out with `where` unless `include_archived`.

        Returns:
            The query document and its variables.

        """
        if meeting_id is not None:
            return cls._HEADLINE_MEETING_LIST_QUERY, {
                "meetingId": meeting_id,
                "includeArchived": include_archived,
            }
        where = None if include_archived else {"archived": {"eq": False}}
        return cls._HEADLINE_USER_LIST_QUERY, {"userId": user_id, "where": where}

    @staticmethod
    def _headlines_from(data: dict[str, Any]) -> list[Headline]:
        """Validate the headlines of a meeting or user list response.

        A response carries either the meeting's connections or the root
        `headlines` connection; the absent ones read as empty.

        Returns:
            The headlines, ordered by creation date.

        """
        nodes = merge_nodes(
            dig_nodes(data, "meeting", "headlines"),
            dig_nodes(data, "meeting", "archivedHeadlines"),
            dig_nodes(data, "headlines"),
        )
        return [Headline.model_validate(node) for node in nodes]

    @staticmethod
    def _headline_create_input(
        *, meeting_id: int, title: str, user_id: int
    ) -> dict[str, Any]:
        """Build the `HeadlineCreateModelInput` fields, apart from notes.

        Returns:
            The input fields.

        """
        return {"title": title, "assignee": user_id, "meetings": [meeting_id]}

    @staticmethod
    def _headline_edit_fields(
        *, title: str | None, user_id: int | None
    ) -> dict[str, Any]:
        """Build the `HeadlineEditModelInput` fields that were given, apart from notes.

        Returns:
            The non-`None` input fields.

        """
        return compact(title=title, assignee=user_id)


class HeadlineOperations(GraphQLOperations, HeadlineOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to headlines."""

    def details(self, headline_id: int) -> Headline:
        """Get details for a headline.

        Args:
            headline_id: The ID of the headline.

        Returns:
            A `Headline` model instance.

        Example:
            ```python
            client.v2.headline.details(123)
            # Returns: Headline(id=123, title='Headline Title', ...)
            ```

        """
        data = self._execute(self._HEADLINE_DETAILS_QUERY, {"id": headline_id})
        return Headline.model_validate(
            self._one(data, "headline", label="Headline", entity_id=headline_id)
        )

    def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        include_archived: bool = False,
    ) -> builtins.list[Headline]:
        """List headlines for a meeting or a user.

        Args:
            meeting_id: The ID of the meeting. Mutually exclusive with
                `user_id`.
            user_id: The ID of the headline owner. Mutually exclusive with
                `meeting_id`. If neither is given, defaults to the current
                user.
            include_archived: If `True`, also include archived headlines.

        Returns:
            A list of `Headline` model instances, ordered by creation date.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        Example:
            ```python
            client.v2.headline.list(meeting_id=349524)
            # Returns: [Headline(id=1, title='Headline 1', ...), ...]
            ```

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = self.user_id
        query, variables = self._headline_list_request(
            meeting_id, user_id, include_archived=include_archived
        )
        return self._headlines_from(self._execute(query, variables))

    def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Headline:
        """Create a new headline.

        Args:
            meeting_id: The ID of the meeting to create the headline in.
                `CreateHeadline` requires exactly one meeting.
            title: The title of the headline.
            user_id: The ID of the headline owner (defaults to the current
                user).
            notes: Description text for the headline.

        Returns:
            The newly created `Headline`.

        Example:
            ```python
            client.v2.headline.create(349524, "New Headline", notes="Details")
            # Returns: Headline(id=456, title='New Headline', ...)
            ```

        """
        if user_id is None:
            user_id = self.user_id
        input_ = self._headline_create_input(
            meeting_id=meeting_id, title=title, user_id=user_id
        )
        result = self._mutate(
            self._HEADLINE_CREATE_MUTATION,
            {"input": {**input_, **self._notes_input(notes)}},
            root_field="CreateHeadline",
            action="create headline",
        )
        return self.details(result["id"])

    def update(
        self,
        headline_id: int,
        *,
        title: str | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Headline:
        """Update an existing headline.

        Args:
            headline_id: The ID of the headline to update.
            title: New title for the headline.
            user_id: New owner for the headline.
            notes: New description text for the headline.

        Returns:
            The updated `Headline`.

        Raises:
            ValueError: If no update fields are provided.

        Example:
            ```python
            client.v2.headline.update(123, title="New Title")
            # Returns: Headline(id=123, title='New Title', ...)
            ```

        """
        fields = self._headline_edit_fields(title=title, user_id=user_id)
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(self._notes_input(notes))
        return self._edit(headline_id, fields, action="update headline")

    def archive(self, headline_id: int) -> Headline:
        """Archive a headline.

        Args:
            headline_id: The ID of the headline to archive.

        Returns:
            The updated `Headline`.

        """
        return self._edit(headline_id, {"archived": True}, action="archive headline")

    def restore(self, headline_id: int) -> Headline:
        """Restore an archived headline.

        Args:
            headline_id: The ID of the headline to restore.

        Returns:
            The updated `Headline`.

        """
        return self._edit(headline_id, {"archived": False}, action="restore headline")

    def _edit(
        self, headline_id: int, fields: dict[str, Any], *, action: str
    ) -> Headline:
        """Run `EditHeadline` with `fields`, then re-read the headline.

        Returns:
            The updated `Headline`.

        """
        self._mutate(
            self._HEADLINE_EDIT_MUTATION,
            {"input": {"headlineId": headline_id, **fields}},
            root_field="EditHeadline",
            action=action,
        )
        return self.details(headline_id)


class AsyncHeadlineOperations(AsyncGraphQLOperations, HeadlineOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to headlines."""

    async def details(self, headline_id: int) -> Headline:
        """Get details for a headline.

        Args:
            headline_id: The ID of the headline.

        Returns:
            A `Headline` model instance.

        """
        data = await self._execute(self._HEADLINE_DETAILS_QUERY, {"id": headline_id})
        return Headline.model_validate(
            self._one(data, "headline", label="Headline", entity_id=headline_id)
        )

    async def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        include_archived: bool = False,
    ) -> builtins.list[Headline]:
        """List headlines for a meeting or a user.

        Args:
            meeting_id: The ID of the meeting. Mutually exclusive with
                `user_id`.
            user_id: The ID of the headline owner. Mutually exclusive with
                `meeting_id`. If neither is given, defaults to the current
                user.
            include_archived: If `True`, also include archived headlines.

        Returns:
            A list of `Headline` model instances, ordered by creation date.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = await self.get_user_id()
        query, variables = self._headline_list_request(
            meeting_id, user_id, include_archived=include_archived
        )
        return self._headlines_from(await self._execute(query, variables))

    async def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Headline:
        """Create a new headline.

        Args:
            meeting_id: The ID of the meeting to create the headline in.
                `CreateHeadline` requires exactly one meeting.
            title: The title of the headline.
            user_id: The ID of the headline owner (defaults to the current
                user).
            notes: Description text for the headline.

        Returns:
            The newly created `Headline`.

        """
        if user_id is None:
            user_id = await self.get_user_id()
        input_ = self._headline_create_input(
            meeting_id=meeting_id, title=title, user_id=user_id
        )
        result = await self._mutate(
            self._HEADLINE_CREATE_MUTATION,
            {"input": {**input_, **await self._notes_input(notes)}},
            root_field="CreateHeadline",
            action="create headline",
        )
        return await self.details(result["id"])

    async def update(
        self,
        headline_id: int,
        *,
        title: str | None = None,
        user_id: int | None = None,
        notes: str | None = None,
    ) -> Headline:
        """Update an existing headline.

        Args:
            headline_id: The ID of the headline to update.
            title: New title for the headline.
            user_id: New owner for the headline.
            notes: New description text for the headline.

        Returns:
            The updated `Headline`.

        Raises:
            ValueError: If no update fields are provided.

        """
        fields = self._headline_edit_fields(title=title, user_id=user_id)
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(await self._notes_input(notes))
        return await self._edit(headline_id, fields, action="update headline")

    async def archive(self, headline_id: int) -> Headline:
        """Archive a headline.

        Args:
            headline_id: The ID of the headline to archive.

        Returns:
            The updated `Headline`.

        """
        return await self._edit(
            headline_id, {"archived": True}, action="archive headline"
        )

    async def restore(self, headline_id: int) -> Headline:
        """Restore an archived headline.

        Args:
            headline_id: The ID of the headline to restore.

        Returns:
            The updated `Headline`.

        """
        return await self._edit(
            headline_id, {"archived": False}, action="restore headline"
        )

    async def _edit(
        self, headline_id: int, fields: dict[str, Any], *, action: str
    ) -> Headline:
        """Run `EditHeadline` with `fields`, then re-read the headline.

        Returns:
            The updated `Headline`.

        """
        await self._mutate(
            self._HEADLINE_EDIT_MUTATION,
            {"input": {"headlineId": headline_id, **fields}},
            root_field="EditHeadline",
            action=action,
        )
        return await self.details(headline_id)
