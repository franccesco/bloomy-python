"""v2: the Bloom Growth GraphQL API.

Exposed as `client.v2` / `AsyncClient().v2`. See `bloomy.v2.base` for the
transport and shared helper conventions, and `bloomy.v2.models` for the
model conventions (owner/related-entity representation, datetime handling,
notes) that every entity added here follows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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


class V2:
    """Namespace for the Bloom Growth GraphQL API (v2) operations.

    Instantiated once by `bloomy.client.Client` and exposed as `client.v2`.
    """

    def __init__(self, client: httpx.Client, graphql_url: str) -> None:
        """Initialize the v2 namespace.

        Args:
            client: The sync HTTP client to use for GraphQL requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        self.user = UserOperations(client, graphql_url)
        self.meeting = MeetingOperations(client, graphql_url)
        self.issue = IssueOperations(client, graphql_url)
        self.headline = HeadlineOperations(client, graphql_url)
        self.todo = TodoOperations(client, graphql_url)
        self.goal = GoalOperations(client, graphql_url)
        self.milestone = MilestoneOperations(client, graphql_url)
        self.metric = MetricOperations(client, graphql_url)


class AsyncV2:
    """Async namespace for the Bloom Growth GraphQL API (v2) operations.

    Instantiated once by `bloomy.async_client.AsyncClient` and exposed as
    `client.v2`.
    """

    def __init__(self, client: httpx.AsyncClient, graphql_url: str) -> None:
        """Initialize the async v2 namespace.

        Args:
            client: The async HTTP client to use for GraphQL requests.
            graphql_url: The absolute URL of the GraphQL endpoint.

        """
        self.user = AsyncUserOperations(client, graphql_url)
        self.meeting = AsyncMeetingOperations(client, graphql_url)
        self.issue = AsyncIssueOperations(client, graphql_url)
        self.headline = AsyncHeadlineOperations(client, graphql_url)
        self.todo = AsyncTodoOperations(client, graphql_url)
        self.goal = AsyncGoalOperations(client, graphql_url)
        self.milestone = AsyncMilestoneOperations(client, graphql_url)
        self.metric = AsyncMetricOperations(client, graphql_url)


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
]
