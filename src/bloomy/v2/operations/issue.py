"""Issue operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import (
    MEETING_REF_FIELDS,
    MUTATION_RESULT_FIELDS,
    NOTES_FIELDS,
    USER_REF_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    compact,
    dig_nodes,
    merge_nodes,
    now_timestamp,
)
from ..models import Issue

_ISSUE_FIELDS = f"""
id
title
recurrenceId
addToDepartmentPlan
completed
completedTimestamp
archived
archivedTimestamp
dateCreated
priorityVoteRank
numStarVotes
issueNumber
{NOTES_FIELDS}
{USER_REF_FIELDS}
"""

_ISSUE_LIST_CONNECTIONS = (
    "issues",
    "longTermIssues",
    "recentlySolvedIssues",
    "archivedIssues",
)


class IssueOperationsMixin:
    """GraphQL documents, inputs, and response parsing shared by issue operations."""

    _ISSUE_DETAILS_QUERY = f"""
    query($id: Long!) {{
      issue(id: $id) {{
        {_ISSUE_FIELDS}
        {MEETING_REF_FIELDS}
      }}
    }}
    """

    # `issues` drops solved and archived issues server-side, and the API stores
    # long-term issues as archived, so each of those lists is its own connection.
    _ISSUE_LIST_QUERY = f"""
    query(
      $meetingId: Long!
      $where: IssueQueryModelFilterInput
      $longTerm: Boolean!
      $includeSolved: Boolean!
      $includeArchived: Boolean!
    ) {{
      meeting(id: $meetingId) {{
        id
        name
        issues(where: $where, order: [{{ dateCreated: ASC }}])
          @skip(if: $longTerm) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
        longTermIssues(where: $where, order: [{{ dateCreated: ASC }}])
          @include(if: $longTerm) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
        recentlySolvedIssues(where: $where, order: [{{ dateCreated: ASC }}])
          @include(if: $includeSolved) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
        archivedIssues(where: $where, order: [{{ dateCreated: ASC }}])
          @include(if: $includeArchived) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _ISSUE_CREATE_MUTATION = f"""
    mutation($input: IssueCreateModelInput!) {{
      CreateIssue(input: $input) {{
        {_ISSUE_FIELDS}
        {MEETING_REF_FIELDS}
      }}
    }}
    """

    _ISSUE_EDIT_MUTATION = f"""
    mutation($input: IssueEditModelInput!) {{
      EditIssue(input: $input) {{
        {MUTATION_RESULT_FIELDS}
      }}
    }}
    """

    @staticmethod
    def _issue_list_variables(
        meeting_id: int,
        *,
        long_term: bool,
        include_solved: bool,
        include_archived: bool,
    ) -> dict[str, Any]:
        """Build the variables for `_ISSUE_LIST_QUERY`.

        Returns:
            The query variables.

        """
        conditions: list[dict[str, Any]] = [{"addToDepartmentPlan": {"eq": long_term}}]
        if not long_term:
            # Drops issues sent to another meeting, as the web app's open list does.
            conditions.append({"sentToIssueMeetingName": {"eq": None}})
        return {
            "meetingId": meeting_id,
            "where": {"and": conditions},
            "longTerm": long_term,
            "includeSolved": include_solved and not long_term,
            "includeArchived": include_archived and not long_term,
        }

    @staticmethod
    def _issues_from(data: dict[str, Any]) -> list[Issue]:
        """Validate the issues of an `_ISSUE_LIST_QUERY` response.

        Every connection is keyed by the issue's recurrence, so each issue's
        meeting ref is the parent meeting's.

        Returns:
            The issues of every selected connection, ordered by creation date.

        """
        meeting: dict[str, Any] = data.get("meeting") or {}
        meeting_ref = {"id": meeting.get("id"), "name": meeting.get("name")}
        nodes = merge_nodes(
            *(dig_nodes(meeting, name) for name in _ISSUE_LIST_CONNECTIONS)
        )
        return [
            Issue.model_validate({**node, "meeting": meeting_ref}) for node in nodes
        ]

    @staticmethod
    def _issue_create_input(
        *, meeting_id: int, title: str, user_id: int, long_term: bool
    ) -> dict[str, Any]:
        """Build the `IssueCreateModelInput` fields, apart from notes.

        Returns:
            The input fields.

        """
        return {
            "title": title,
            "ownerId": user_id,
            "recurrenceId": meeting_id,
            "addToDepartmentPlan": long_term,
        }

    @staticmethod
    def _issue_edit_fields(
        *,
        title: str | None,
        user_id: int | None,
        long_term: bool | None,
        meeting_id: int | None,
    ) -> dict[str, Any]:
        """Build the `IssueEditModelInput` fields that were given, apart from notes.

        Returns:
            The non-`None` input fields.

        """
        return compact(
            title=title,
            assigneeId=user_id,
            addToDepartmentPlan=long_term,
            meetingId=meeting_id,
        )


class IssueOperations(GraphQLOperations, IssueOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to issues."""

    def details(self, issue_id: int) -> Issue:
        """Get details for an issue.

        Args:
            issue_id: The ID of the issue.

        Returns:
            An `Issue` model instance.

        Example:
            ```python
            client.v2.issue.details(123)
            # Returns: Issue(id=123, title='Issue Title', ...)
            ```

        """
        data = self._execute(self._ISSUE_DETAILS_QUERY, {"id": issue_id})
        return Issue.model_validate(
            self._one(data, "issue", label="Issue", entity_id=issue_id)
        )

    def list(
        self,
        meeting_id: int,
        *,
        long_term: bool = False,
        include_solved: bool = False,
        include_archived: bool = False,
    ) -> builtins.list[Issue]:
        """List issues for a meeting.

        Args:
            meeting_id: The ID of the meeting.
            long_term: If `True`, list long-term (department plan) issues
                instead of short-term ones. `include_solved` and
                `include_archived` have no effect in this mode.
            include_solved: If `True`, also include recently solved issues.
            include_archived: If `True`, also include archived issues.

        Returns:
            A list of `Issue` model instances, ordered by creation date.

        Example:
            ```python
            client.v2.issue.list(349524)
            # Returns: [Issue(id=1, title='Issue 1', ...), ...]
            ```

        """
        variables = self._issue_list_variables(
            meeting_id,
            long_term=long_term,
            include_solved=include_solved,
            include_archived=include_archived,
        )
        return self._issues_from(self._execute(self._ISSUE_LIST_QUERY, variables))

    def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        notes: str | None = None,
        long_term: bool = False,
    ) -> Issue:
        """Create a new issue.

        Args:
            meeting_id: The ID of the meeting to create the issue in. For L10
                meetings this doubles as the recurrence id `CreateIssue` needs.
            title: The title of the issue.
            user_id: The ID of the issue owner (defaults to the current user).
            notes: Description text for the issue.
            long_term: Whether to create it directly as a long-term
                (department plan) issue.

        Returns:
            The newly created `Issue`.

        Example:
            ```python
            client.v2.issue.create(349524, "New Issue", notes="Details")
            # Returns: Issue(id=456, title='New Issue', ...)
            ```

        """
        if user_id is None:
            user_id = self.user_id
        input_ = self._issue_create_input(
            meeting_id=meeting_id, title=title, user_id=user_id, long_term=long_term
        )
        result = self._mutate(
            self._ISSUE_CREATE_MUTATION,
            {"input": {**input_, **self._notes_input(notes)}},
            root_field="CreateIssue",
            action="create issue",
        )
        return Issue.model_validate(result)

    def update(
        self,
        issue_id: int,
        *,
        title: str | None = None,
        user_id: int | None = None,
        notes: str | None = None,
        long_term: bool | None = None,
        meeting_id: int | None = None,
    ) -> Issue:
        """Update an existing issue.

        Args:
            issue_id: The ID of the issue to update.
            title: New title for the issue.
            user_id: New owner for the issue.
            notes: New description text for the issue.
            long_term: Move the issue to/from the long-term (department plan)
                list.
            meeting_id: Move the issue to a different meeting.

        Returns:
            The updated `Issue`.

        Raises:
            ValueError: If no update fields are provided.

        Example:
            ```python
            client.v2.issue.update(123, title="New Title")
            # Returns: Issue(id=123, title='New Title', ...)
            ```

        """
        fields = self._issue_edit_fields(
            title=title, user_id=user_id, long_term=long_term, meeting_id=meeting_id
        )
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(self._notes_input(notes))
        return self._edit(issue_id, fields, action="update issue")

    def solve(self, issue_id: int) -> Issue:
        """Mark an issue as solved.

        Note:
            Verified live: this has no effect on an already-archived issue
            (including a long-term one) — `completedTimestamp` is updated but
            `completed` stays `False`. Solve issues before archiving them.

        Args:
            issue_id: The ID of the issue to solve.

        Returns:
            The updated `Issue`.

        """
        return self._edit(
            issue_id,
            {"completed": True, "completedTimestamp": now_timestamp()},
            action="solve issue",
        )

    def reopen(self, issue_id: int) -> Issue:
        """Reopen a solved issue.

        Args:
            issue_id: The ID of the issue to reopen.

        Returns:
            The updated `Issue`.

        """
        return self._edit(
            issue_id,
            {"completed": False, "completedTimestamp": None},
            action="reopen issue",
        )

    def archive(self, issue_id: int) -> Issue:
        """Archive an issue.

        Args:
            issue_id: The ID of the issue to archive.

        Returns:
            The updated `Issue`.

        """
        return self._edit(issue_id, {"archived": True}, action="archive issue")

    def restore(self, issue_id: int) -> Issue:
        """Restore an archived issue.

        An archived long-term issue is restored to the short-term list,
        because archiving it removed it from the long-term list.

        Args:
            issue_id: The ID of the issue to restore.

        Returns:
            The updated `Issue`.

        """
        return self._edit(issue_id, {"archived": False}, action="restore issue")

    def _edit(self, issue_id: int, fields: dict[str, Any], *, action: str) -> Issue:
        """Run `EditIssue` with `fields`, then re-read the issue.

        Returns:
            The updated `Issue`.

        """
        self._mutate(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, **fields}},
            root_field="EditIssue",
            action=action,
        )
        return self.details(issue_id)


class AsyncIssueOperations(AsyncGraphQLOperations, IssueOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to issues."""

    async def details(self, issue_id: int) -> Issue:
        """Get details for an issue.

        Args:
            issue_id: The ID of the issue.

        Returns:
            An `Issue` model instance.

        """
        data = await self._execute(self._ISSUE_DETAILS_QUERY, {"id": issue_id})
        return Issue.model_validate(
            self._one(data, "issue", label="Issue", entity_id=issue_id)
        )

    async def list(
        self,
        meeting_id: int,
        *,
        long_term: bool = False,
        include_solved: bool = False,
        include_archived: bool = False,
    ) -> builtins.list[Issue]:
        """List issues for a meeting.

        Args:
            meeting_id: The ID of the meeting.
            long_term: If `True`, list long-term (department plan) issues
                instead of short-term ones. `include_solved` and
                `include_archived` have no effect in this mode.
            include_solved: If `True`, also include recently solved issues.
            include_archived: If `True`, also include archived issues.

        Returns:
            A list of `Issue` model instances, ordered by creation date.

        """
        variables = self._issue_list_variables(
            meeting_id,
            long_term=long_term,
            include_solved=include_solved,
            include_archived=include_archived,
        )
        return self._issues_from(await self._execute(self._ISSUE_LIST_QUERY, variables))

    async def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        notes: str | None = None,
        long_term: bool = False,
    ) -> Issue:
        """Create a new issue.

        Args:
            meeting_id: The ID of the meeting to create the issue in. For L10
                meetings this doubles as the recurrence id `CreateIssue` needs.
            title: The title of the issue.
            user_id: The ID of the issue owner (defaults to the current user).
            notes: Description text for the issue.
            long_term: Whether to create it directly as a long-term
                (department plan) issue.

        Returns:
            The newly created `Issue`.

        """
        if user_id is None:
            user_id = await self.get_user_id()
        input_ = self._issue_create_input(
            meeting_id=meeting_id, title=title, user_id=user_id, long_term=long_term
        )
        result = await self._mutate(
            self._ISSUE_CREATE_MUTATION,
            {"input": {**input_, **await self._notes_input(notes)}},
            root_field="CreateIssue",
            action="create issue",
        )
        return Issue.model_validate(result)

    async def update(
        self,
        issue_id: int,
        *,
        title: str | None = None,
        user_id: int | None = None,
        notes: str | None = None,
        long_term: bool | None = None,
        meeting_id: int | None = None,
    ) -> Issue:
        """Update an existing issue.

        Args:
            issue_id: The ID of the issue to update.
            title: New title for the issue.
            user_id: New owner for the issue.
            notes: New description text for the issue.
            long_term: Move the issue to/from the long-term (department plan)
                list.
            meeting_id: Move the issue to a different meeting.

        Returns:
            The updated `Issue`.

        Raises:
            ValueError: If no update fields are provided.

        """
        fields = self._issue_edit_fields(
            title=title, user_id=user_id, long_term=long_term, meeting_id=meeting_id
        )
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        fields.update(await self._notes_input(notes))
        return await self._edit(issue_id, fields, action="update issue")

    async def solve(self, issue_id: int) -> Issue:
        """Mark an issue as solved.

        Note:
            Verified live: this has no effect on an already-archived issue
            (including a long-term one) — `completedTimestamp` is updated but
            `completed` stays `False`. Solve issues before archiving them.

        Args:
            issue_id: The ID of the issue to solve.

        Returns:
            The updated `Issue`.

        """
        return await self._edit(
            issue_id,
            {"completed": True, "completedTimestamp": now_timestamp()},
            action="solve issue",
        )

    async def reopen(self, issue_id: int) -> Issue:
        """Reopen a solved issue.

        Args:
            issue_id: The ID of the issue to reopen.

        Returns:
            The updated `Issue`.

        """
        return await self._edit(
            issue_id,
            {"completed": False, "completedTimestamp": None},
            action="reopen issue",
        )

    async def archive(self, issue_id: int) -> Issue:
        """Archive an issue.

        Args:
            issue_id: The ID of the issue to archive.

        Returns:
            The updated `Issue`.

        """
        return await self._edit(issue_id, {"archived": True}, action="archive issue")

    async def restore(self, issue_id: int) -> Issue:
        """Restore an archived issue.

        An archived long-term issue is restored to the short-term list,
        because archiving it removed it from the long-term list.

        Args:
            issue_id: The ID of the issue to restore.

        Returns:
            The updated `Issue`.

        """
        return await self._edit(issue_id, {"archived": False}, action="restore issue")

    async def _edit(
        self, issue_id: int, fields: dict[str, Any], *, action: str
    ) -> Issue:
        """Run `EditIssue` with `fields`, then re-read the issue.

        Returns:
            The updated `Issue`.

        """
        await self._mutate(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, **fields}},
            root_field="EditIssue",
            action=action,
        )
        return await self.details(issue_id)
