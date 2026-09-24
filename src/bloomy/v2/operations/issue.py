"""Issue operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ..base import (
    MUTATION_RESULT_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    dig_nodes,
    extract_notes,
)
from ..models import Issue

_ISSUE_FIELDS = """
id
title
recurrenceId
addToDepartmentPlan
notesId
notesText
localHtml
collaborationEnabled
completed
completedTimestamp
archived
archivedTimestamp
dateCreated
priorityVoteRank
numStarVotes
issueNumber
assignee { id fullName }
meeting { id name }
"""


class IssueOperationsMixin:
    """Shared GraphQL documents and response transforms for issue operations."""

    _ISSUE_DETAILS_QUERY = f"""
    query($id: Long!) {{
      issue(id: $id) {{
        {_ISSUE_FIELDS}
      }}
    }}
    """

    # `meeting.issues` excludes solved and archived issues unconditionally
    # (it filters `CloseTime == null` server-side); `recentlySolvedIssues`
    # and `archivedIssues` are separate connections for those.
    _ISSUE_LIST_QUERY = f"""
    query($meetingId: Long!, $where: IssueQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        issues(where: $where, order: [{{ dateCreated: ASC }}]) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
      }}
    }}
    """

    # The API stores every long-term (department plan) issue with
    # `archived: true`, so `meeting.issues` (which drops archived issues
    # server-side) never returns them; this dedicated connection does.
    _ISSUE_LONG_TERM_QUERY = f"""
    query($meetingId: Long!, $where: IssueQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        longTermIssues(where: $where, order: [{{ dateCreated: ASC }}]) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _ISSUE_SOLVED_QUERY = f"""
    query($meetingId: Long!, $where: IssueQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        recentlySolvedIssues(where: $where, order: [{{ dateCreated: ASC }}]) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _ISSUE_ARCHIVED_QUERY = f"""
    query($meetingId: Long!, $where: IssueQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        archivedIssues(where: $where, order: [{{ dateCreated: ASC }}]) {{
          nodes {{
            {_ISSUE_FIELDS}
          }}
        }}
      }}
    }}
    """

    _ISSUE_CREATE_MUTATION = """
    mutation($input: IssueCreateModelInput!) {
      CreateIssue(input: $input) {
        id
      }
    }
    """

    _ISSUE_EDIT_MUTATION = f"""
    mutation($input: IssueEditModelInput!) {{
      EditIssue(input: $input) {{
        {MUTATION_RESULT_FIELDS}
      }}
    }}
    """

    def _issue_where(self, *, long_term: bool) -> dict[str, Any]:
        """Build the base `where` filter shared by every issue list connection.

        Returns:
            An `IssueQueryModelFilterInput`-shaped dictionary.

        """
        conditions: list[dict[str, Any]] = [{"addToDepartmentPlan": {"eq": long_term}}]
        if not long_term:
            # Excludes issues sent to another meeting; only meaningful for the
            # short-term open list (mirrors the web app's own query).
            conditions.append({"sentToIssueMeetingName": {"eq": None}})
        return {"and": conditions}

    def _transform_issue(self, data: dict[str, Any]) -> Issue:
        """Transform a raw GraphQL issue object into an `Issue` model.

        The API reports every long-term issue as archived, while the web app
        lists them on the Long-Term tab. Archiving a long-term issue clears
        `addToDepartmentPlan`, so an issue counts as archived only when it is
        archived and not long-term.

        Returns:
            An `Issue` model instance.

        """
        fields: dict[str, Any] = {
            **data,
            "archived": bool(data.get("archived"))
            and not data.get("addToDepartmentPlan"),
        }
        return Issue(**fields, notes=extract_notes(data))


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
        return self._transform_issue(data["issue"])

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
        where = self._issue_where(long_term=long_term)

        if long_term:
            data = self._execute(
                self._ISSUE_LONG_TERM_QUERY, {"meetingId": meeting_id, "where": where}
            )
            nodes = dig_nodes(data, "meeting", "longTermIssues")
            return [self._transform_issue(node) for node in nodes]

        data = self._execute(
            self._ISSUE_LIST_QUERY, {"meetingId": meeting_id, "where": where}
        )
        nodes = dig_nodes(data, "meeting", "issues")

        if include_solved:
            solved_data = self._execute(
                self._ISSUE_SOLVED_QUERY, {"meetingId": meeting_id, "where": where}
            )
            nodes += dig_nodes(solved_data, "meeting", "recentlySolvedIssues")

        if include_archived:
            archived_data = self._execute(
                self._ISSUE_ARCHIVED_QUERY, {"meetingId": meeting_id, "where": where}
            )
            nodes += dig_nodes(archived_data, "meeting", "archivedIssues")

        seen: dict[int, dict[str, Any]] = {}
        for node in nodes:
            seen.setdefault(node["id"], node)
        return [self._transform_issue(node) for node in seen.values()]

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

        input_: dict[str, Any] = {
            "title": title,
            "ownerId": user_id,
            "recurrenceId": meeting_id,
            "addToDepartmentPlan": long_term,
        }
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = self._execute(self._ISSUE_CREATE_MUTATION, {"input": input_})
        return self.details(data["CreateIssue"]["id"])

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
        if (
            title is None
            and user_id is None
            and notes is None
            and long_term is None
            and meeting_id is None
        ):
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"id": issue_id}
        if title is not None:
            input_["title"] = title
        if user_id is not None:
            input_["assigneeId"] = user_id
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True
        if long_term is not None:
            input_["addToDepartmentPlan"] = long_term
        if meeting_id is not None:
            input_["meetingId"] = meeting_id

        self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": input_},
            root_field="EditIssue",
            action="update issue",
        )
        return self.details(issue_id)

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
        self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {
                "input": {
                    "id": issue_id,
                    "completed": True,
                    "completedTimestamp": self._now_timestamp(),
                }
            },
            root_field="EditIssue",
            action="solve issue",
        )
        return self.details(issue_id)

    def reopen(self, issue_id: int) -> Issue:
        """Reopen a solved issue.

        Args:
            issue_id: The ID of the issue to reopen.

        Returns:
            The updated `Issue`.

        """
        self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, "completed": False, "completedTimestamp": None}},
            root_field="EditIssue",
            action="reopen issue",
        )
        return self.details(issue_id)

    def archive(self, issue_id: int) -> Issue:
        """Archive an issue.

        Args:
            issue_id: The ID of the issue to archive.

        Returns:
            The updated `Issue`.

        """
        self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, "archived": True}},
            root_field="EditIssue",
            action="archive issue",
        )
        return self.details(issue_id)

    def restore(self, issue_id: int) -> Issue:
        """Restore an archived issue.

        An archived long-term issue is restored to the short-term list,
        because archiving it removed it from the long-term list.

        Args:
            issue_id: The ID of the issue to restore.

        Returns:
            The updated `Issue`.

        """
        self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, "archived": False}},
            root_field="EditIssue",
            action="restore issue",
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
        return self._transform_issue(data["issue"])

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
        where = self._issue_where(long_term=long_term)

        if long_term:
            data = await self._execute(
                self._ISSUE_LONG_TERM_QUERY, {"meetingId": meeting_id, "where": where}
            )
            nodes = dig_nodes(data, "meeting", "longTermIssues")
            return [self._transform_issue(node) for node in nodes]

        data = await self._execute(
            self._ISSUE_LIST_QUERY, {"meetingId": meeting_id, "where": where}
        )
        nodes = dig_nodes(data, "meeting", "issues")

        if include_solved:
            solved_data = await self._execute(
                self._ISSUE_SOLVED_QUERY, {"meetingId": meeting_id, "where": where}
            )
            nodes += dig_nodes(solved_data, "meeting", "recentlySolvedIssues")

        if include_archived:
            archived_data = await self._execute(
                self._ISSUE_ARCHIVED_QUERY, {"meetingId": meeting_id, "where": where}
            )
            nodes += dig_nodes(archived_data, "meeting", "archivedIssues")

        seen: dict[int, dict[str, Any]] = {}
        for node in nodes:
            seen.setdefault(node["id"], node)
        return [self._transform_issue(node) for node in seen.values()]

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

        input_: dict[str, Any] = {
            "title": title,
            "ownerId": user_id,
            "recurrenceId": meeting_id,
            "addToDepartmentPlan": long_term,
        }
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = await self._execute(self._ISSUE_CREATE_MUTATION, {"input": input_})
        return await self.details(data["CreateIssue"]["id"])

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
        if (
            title is None
            and user_id is None
            and notes is None
            and long_term is None
            and meeting_id is None
        ):
            raise ValueError("At least one field must be provided for update")

        input_: dict[str, Any] = {"id": issue_id}
        if title is not None:
            input_["title"] = title
        if user_id is not None:
            input_["assigneeId"] = user_id
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True
        if long_term is not None:
            input_["addToDepartmentPlan"] = long_term
        if meeting_id is not None:
            input_["meetingId"] = meeting_id

        await self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": input_},
            root_field="EditIssue",
            action="update issue",
        )
        return await self.details(issue_id)

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
        await self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {
                "input": {
                    "id": issue_id,
                    "completed": True,
                    "completedTimestamp": self._now_timestamp(),
                }
            },
            root_field="EditIssue",
            action="solve issue",
        )
        return await self.details(issue_id)

    async def reopen(self, issue_id: int) -> Issue:
        """Reopen a solved issue.

        Args:
            issue_id: The ID of the issue to reopen.

        Returns:
            The updated `Issue`.

        """
        await self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, "completed": False, "completedTimestamp": None}},
            root_field="EditIssue",
            action="reopen issue",
        )
        return await self.details(issue_id)

    async def archive(self, issue_id: int) -> Issue:
        """Archive an issue.

        Args:
            issue_id: The ID of the issue to archive.

        Returns:
            The updated `Issue`.

        """
        await self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, "archived": True}},
            root_field="EditIssue",
            action="archive issue",
        )
        return await self.details(issue_id)

    async def restore(self, issue_id: int) -> Issue:
        """Restore an archived issue.

        An archived long-term issue is restored to the short-term list,
        because archiving it removed it from the long-term list.

        Args:
            issue_id: The ID of the issue to restore.

        Returns:
            The updated `Issue`.

        """
        await self._run_mutation(
            self._ISSUE_EDIT_MUTATION,
            {"input": {"id": issue_id, "archived": False}},
            root_field="EditIssue",
            action="restore issue",
        )
        return await self.details(issue_id)
