"""Headline operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import (
    AsyncGraphQLOperations,
    GraphQLOperations,
    dig_nodes,
    extract_notes,
    merge_nodes,
)
from ..models import Headline

_HEADLINE_FIELDS = """
id
title
recurrenceId
notesId
notesText
localHtml
collaborationEnabled
archived
archivedTimestamp
dateCreated
assignee { id fullName }
meeting { id name }
"""


class HeadlineOperationsMixin:
    """Shared GraphQL documents and response transforms for headline operations."""

    _HEADLINE_DETAILS_QUERY = f"""
    query($id: Long!) {{
      headline(id: $id) {{
        {_HEADLINE_FIELDS}
      }}
    }}
    """

    # `meeting.headlines` returns only OPEN headlines (`CloseTime == null`);
    # `meeting.archivedHeadlines` is a separate connection for archived ones,
    # selected conditionally in this one document via `@include` so `list()`
    # never issues more than one request. Verified live against production
    # (`archivedHeadlines` is omitted from the response entirely when
    # `$includeArchived` is `false`).
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

    # Root `headlines(userId)` returns every headline owned by the user,
    # archived ones included, with no way to filter server-side beyond
    # `where`; filtering is done client-side in `list()` instead.
    _HEADLINE_USER_LIST_QUERY = f"""
    query($userId: Long!) {{
      headlines(userId: $userId, order: [{{ dateCreated: ASC }}]) {{
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

    # `EditHeadline` returns `IdModel { id }`, not the
    # `{success message errorDetails}` shape `EditIssue` returns, so it is
    # run with a plain `_execute` rather than `_run_mutation`; a failure
    # surfaces as a top-level GraphQL `errors` entry instead.
    _HEADLINE_EDIT_MUTATION = """
    mutation($input: HeadlineEditModelInput!) {
      EditHeadline(input: $input) {
        id
      }
    }
    """

    def _transform_headline(self, data: dict[str, Any]) -> Headline:
        """Transform a raw GraphQL headline object into a `Headline` model.

        Returns:
            A `Headline` model instance.

        """
        return Headline(**data, notes=extract_notes(data))


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
        return self._transform_headline(
            self._require_entity(data, "headline", headline_id, "Headline")
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

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        if meeting_id is not None:
            data = self._execute(
                self._HEADLINE_MEETING_LIST_QUERY,
                {"meetingId": meeting_id, "includeArchived": include_archived},
            )
            merged = merge_nodes(
                dig_nodes(data, "meeting", "headlines"),
                dig_nodes(data, "meeting", "archivedHeadlines"),
            )
            return [self._transform_headline(node) for node in merged]

        if user_id is None:
            user_id = self.user_id
        data = self._execute(self._HEADLINE_USER_LIST_QUERY, {"userId": user_id})
        nodes = dig_nodes(data, "headlines")
        if not include_archived:
            nodes = [node for node in nodes if not node.get("archived")]
        return [self._transform_headline(node) for node in nodes]

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

        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "meetings": [meeting_id],
        }
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = self._execute(self._HEADLINE_CREATE_MUTATION, {"input": input_})
        headline_id = self._require_created_id(
            data.get("CreateHeadline"), label="headline"
        )
        return self.details(headline_id)

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
        if title is None and user_id is None and notes is None:
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"headlineId": headline_id}
        if title is not None:
            input_["title"] = title
        if user_id is not None:
            input_["assignee"] = user_id
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        self._execute(self._HEADLINE_EDIT_MUTATION, {"input": input_})
        return self.details(headline_id)

    def archive(self, headline_id: int) -> Headline:
        """Archive a headline.

        Args:
            headline_id: The ID of the headline to archive.

        Returns:
            The updated `Headline`.

        """
        self._execute(
            self._HEADLINE_EDIT_MUTATION,
            {"input": {"headlineId": headline_id, "archived": True}},
        )
        return self.details(headline_id)

    def restore(self, headline_id: int) -> Headline:
        """Restore an archived headline.

        Args:
            headline_id: The ID of the headline to restore.

        Returns:
            The updated `Headline`.

        """
        self._execute(
            self._HEADLINE_EDIT_MUTATION,
            {"input": {"headlineId": headline_id, "archived": False}},
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
        return self._transform_headline(
            self._require_entity(data, "headline", headline_id, "Headline")
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

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        if meeting_id is not None:
            data = await self._execute(
                self._HEADLINE_MEETING_LIST_QUERY,
                {"meetingId": meeting_id, "includeArchived": include_archived},
            )
            merged = merge_nodes(
                dig_nodes(data, "meeting", "headlines"),
                dig_nodes(data, "meeting", "archivedHeadlines"),
            )
            return [self._transform_headline(node) for node in merged]

        if user_id is None:
            user_id = await self.get_user_id()
        data = await self._execute(self._HEADLINE_USER_LIST_QUERY, {"userId": user_id})
        nodes = dig_nodes(data, "headlines")
        if not include_archived:
            nodes = [node for node in nodes if not node.get("archived")]
        return [self._transform_headline(node) for node in nodes]

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

        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "meetings": [meeting_id],
        }
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = await self._execute(self._HEADLINE_CREATE_MUTATION, {"input": input_})
        headline_id = self._require_created_id(
            data.get("CreateHeadline"), label="headline"
        )
        return await self.details(headline_id)

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
        if title is None and user_id is None and notes is None:
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"headlineId": headline_id}
        if title is not None:
            input_["title"] = title
        if user_id is not None:
            input_["assignee"] = user_id
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        await self._execute(self._HEADLINE_EDIT_MUTATION, {"input": input_})
        return await self.details(headline_id)

    async def archive(self, headline_id: int) -> Headline:
        """Archive a headline.

        Args:
            headline_id: The ID of the headline to archive.

        Returns:
            The updated `Headline`.

        """
        await self._execute(
            self._HEADLINE_EDIT_MUTATION,
            {"input": {"headlineId": headline_id, "archived": True}},
        )
        return await self.details(headline_id)

    async def restore(self, headline_id: int) -> Headline:
        """Restore an archived headline.

        Args:
            headline_id: The ID of the headline to restore.

        Returns:
            The updated `Headline`.

        """
        await self._execute(
            self._HEADLINE_EDIT_MUTATION,
            {"input": {"headlineId": headline_id, "archived": False}},
        )
        return await self.details(headline_id)
