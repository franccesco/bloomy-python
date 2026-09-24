"""v2: the Bloom Growth GraphQL API.

Exposed as `client.v2` / `AsyncClient().v2`. See `bloomy.v2.base` for the
transport and shared helpers, and `bloomy.v2.models` for the model
conventions every entity here follows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from .base import UserIdCache
from .models import (
    Goal,
    GoalStatus,
    Headline,
    Issue,
    Meeting,
    MeetingListItem,
    MeetingRef,
    Metric,
    MetricFrequency,
    MetricRule,
    MetricScore,
    MetricUnit,
    Milestone,
    Todo,
    User,
    UserRef,
)
from .operations import (
    AsyncGoalOperations,
    AsyncHeadlineOperations,
    AsyncIssueOperations,
    AsyncMeetingOperations,
    AsyncMetricOperations,
    AsyncMilestoneOperations,
    AsyncTodoOperations,
    AsyncUserOperations,
    GoalOperations,
    HeadlineOperations,
    IssueOperations,
    MeetingOperations,
    MetricOperations,
    MilestoneOperations,
    TodoOperations,
    UserOperations,
)

if TYPE_CHECKING:
    import httpx


def default_graphql_url(base_url: str) -> str:
    """Derive the GraphQL endpoint from the REST base URL.

    Args:
        base_url: The v1 REST base URL (e.g. `https://app.bloomgrowth.com/api/v1`).

    Returns:
        The scheme and host of `base_url` plus `/graphql/`.

    """
    parsed = urlsplit(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/graphql/"


class V2:
    """Namespace for the Bloom Growth GraphQL API (v2) operations.

    Instantiated once by `bloomy.client.Client` and exposed as `client.v2`.
    Every operations object shares one cached current-user id.
    """

    def __init__(self, client: httpx.Client, graphql_url: str) -> None:
        """Initialize the v2 namespace.

        Args:
            client: The sync HTTP client to use for GraphQL requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        args = (client, graphql_url, UserIdCache())
        self.user = UserOperations(*args)
        self.meeting = MeetingOperations(*args)
        self.issue = IssueOperations(*args)
        self.headline = HeadlineOperations(*args)
        self.todo = TodoOperations(*args)
        self.goal = GoalOperations(*args)
        self.milestone = MilestoneOperations(*args)
        self.metric = MetricOperations(*args)


class AsyncV2:
    """Async namespace for the Bloom Growth GraphQL API (v2) operations.

    Instantiated once by `bloomy.async_client.AsyncClient` and exposed as
    `client.v2`. Every operations object shares one cached current-user id.
    """

    def __init__(self, client: httpx.AsyncClient, graphql_url: str) -> None:
        """Initialize the async v2 namespace.

        Args:
            client: The async HTTP client to use for GraphQL requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        args = (client, graphql_url, UserIdCache())
        self.user = AsyncUserOperations(*args)
        self.meeting = AsyncMeetingOperations(*args)
        self.issue = AsyncIssueOperations(*args)
        self.headline = AsyncHeadlineOperations(*args)
        self.todo = AsyncTodoOperations(*args)
        self.goal = AsyncGoalOperations(*args)
        self.milestone = AsyncMilestoneOperations(*args)
        self.metric = AsyncMetricOperations(*args)


__all__ = [
    "V2",
    "AsyncV2",
    "Goal",
    "GoalStatus",
    "Headline",
    "Issue",
    "Meeting",
    "MeetingListItem",
    "MeetingRef",
    "Metric",
    "MetricFrequency",
    "MetricRule",
    "MetricScore",
    "MetricUnit",
    "Milestone",
    "Todo",
    "User",
    "UserRef",
    "default_graphql_url",
]
