"""v1: the Bloom Growth REST API (unchanged from earlier SDK releases).

Exposed as `client.v1` / `AsyncClient().v1`. The top-level attributes on
`Client`/`AsyncClient` (`client.user`, `client.meeting`, ...) are aliases
pointing at the SAME operation instances held here, kept for backward
compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..operations.async_.goals import AsyncGoalOperations
from ..operations.async_.headlines import AsyncHeadlineOperations
from ..operations.async_.issues import AsyncIssueOperations
from ..operations.async_.meetings import AsyncMeetingOperations
from ..operations.async_.scorecard import AsyncScorecardOperations
from ..operations.async_.todos import AsyncTodoOperations
from ..operations.async_.users import AsyncUserOperations
from ..operations.goals import GoalOperations
from ..operations.headlines import HeadlineOperations
from ..operations.issues import IssueOperations
from ..operations.meetings import MeetingOperations
from ..operations.scorecard import ScorecardOperations
from ..operations.todos import TodoOperations
from ..operations.users import UserOperations

if TYPE_CHECKING:
    import httpx


class V1:
    """Namespace for the Bloom Growth REST API (v1) operations.

    Instantiated once by `bloomy.client.Client` and exposed as `client.v1`.
    """

    def __init__(self, client: httpx.Client) -> None:
        """Initialize the v1 namespace.

        Args:
            client: The sync HTTP client to use for REST requests.

        """
        self.user = UserOperations(client)
        self.todo = TodoOperations(client)
        self.meeting = MeetingOperations(client)
        self.goal = GoalOperations(client)
        self.scorecard = ScorecardOperations(client)
        self.issue = IssueOperations(client)
        self.headline = HeadlineOperations(client)


class AsyncV1:
    """Async namespace for the Bloom Growth REST API (v1) operations.

    Instantiated once by `bloomy.async_client.AsyncClient` and exposed as
    `client.v1`.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Initialize the async v1 namespace.

        Args:
            client: The async HTTP client to use for REST requests.

        """
        self.user = AsyncUserOperations(client)
        self.meeting = AsyncMeetingOperations(client)
        self.todo = AsyncTodoOperations(client)
        self.goal = AsyncGoalOperations(client)
        self.headline = AsyncHeadlineOperations(client)
        self.issue = AsyncIssueOperations(client)
        self.scorecard = AsyncScorecardOperations(client)


__all__ = ["V1", "AsyncV1"]
