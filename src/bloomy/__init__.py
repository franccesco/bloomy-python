"""Bloomy - Python SDK for Bloom Growth API."""

import importlib.metadata

from .async_client import AsyncClient
from .client import Client
from .configuration import Configuration
from .exceptions import APIError, AuthenticationError, BloomyError, ConfigurationError
from .models import (
    ArchivedGoalInfo,
    CreatedGoalInfo,
    CreatedIssue,
    CurrentWeek,
    DirectReport,
    Goal,
    GoalInfo,
    GoalListResponse,
    GoalStatus,
    Headline,
    HeadlineDetails,
    HeadlineInfo,
    HeadlineListItem,
    Issue,
    IssueDetails,
    IssueListItem,
    Meeting,
    MeetingAttendee,
    MeetingDetails,
    MeetingInfo,
    MeetingListItem,
    OwnerDetails,
    Position,
    ScorecardItem,
    ScorecardMetric,
    ScorecardWeek,
    Todo,
    UserDetails,
    UserListItem,
    UserSearchResult,
)

try:
    __version__ = importlib.metadata.version("bloomy")
except importlib.metadata.PackageNotFoundError:
    __version__ = "unknown"
__all__ = [
    "APIError",
    "ArchivedGoalInfo",
    "AsyncClient",
    "AuthenticationError",
    "BloomyError",
    "Client",
    "Configuration",
    "ConfigurationError",
    "CreatedGoalInfo",
    "CreatedIssue",
    "CurrentWeek",
    "DirectReport",
    "Goal",
    "GoalInfo",
    "GoalListResponse",
    "GoalStatus",
    "Headline",
    "HeadlineDetails",
    "HeadlineInfo",
    "HeadlineListItem",
    "Issue",
    "IssueDetails",
    "IssueListItem",
    "Meeting",
    "MeetingAttendee",
    "MeetingDetails",
    "MeetingInfo",
    "MeetingListItem",
    "OwnerDetails",
    "Position",
    "ScorecardItem",
    "ScorecardMetric",
    "ScorecardWeek",
    "Todo",
    "UserDetails",
    "UserListItem",
    "UserSearchResult",
]
