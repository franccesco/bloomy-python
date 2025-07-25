"""Pydantic models for the Bloomy SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BloomyBaseModel(BaseModel):
    """Base model with common configuration for all Bloomy models."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
    )


class DirectReport(BloomyBaseModel):
    """Model for direct report information."""

    id: int
    name: str
    image_url: str


class Position(BloomyBaseModel):
    """Model for position information."""

    id: int
    name: str


class UserDetails(BloomyBaseModel):
    """Model for user details."""

    id: int
    name: str
    image_url: str
    direct_reports: list[DirectReport] | None = None
    positions: list[Position] | None = None


class UserSearchResult(BloomyBaseModel):
    """Model for user search results."""

    id: int
    name: str
    description: str
    email: str
    organization_id: int
    image_url: str


class UserListItem(BloomyBaseModel):
    """Model for user list items."""

    id: int
    name: str
    email: str
    position: str
    image_url: str


class MeetingAttendee(BloomyBaseModel):
    """Model for meeting attendee."""

    user_id: int = Field(alias="UserId")
    name: str = Field(alias="Name")
    image_url: str = Field(alias="ImageUrl")


class MeetingListItem(BloomyBaseModel):
    """Model for meeting list item (simplified response)."""

    id: int = Field(alias="Id")
    type: str = Field(alias="Type")
    key: str = Field(alias="Key")
    name: str = Field(alias="Name")


class Meeting(BloomyBaseModel):
    """Model for meeting."""

    id: int = Field(alias="Id")
    name: str = Field(alias="Name")
    start_date_utc: datetime = Field(alias="StartDateUtc")
    created_date: datetime = Field(alias="CreateDate")
    organization_id: int = Field(alias="OrganizationId")


class MeetingDetails(BloomyBaseModel):
    """Model for meeting details."""

    id: int
    name: str
    start_date_utc: datetime | None = None
    created_date: datetime | None = None
    organization_id: int | None = None
    attendees: list[MeetingAttendee] | None = None
    issues: list[Issue] | None = None
    todos: list[Todo] | None = None
    metrics: list[ScorecardMetric] | None = None


class Todo(BloomyBaseModel):
    """Model for todo."""

    id: int = Field(alias="Id")
    name: str = Field(alias="Name")
    details_url: str | None = Field(alias="DetailsUrl", default=None)
    due_date: datetime | None = Field(alias="DueDate", default=None)
    complete_date: datetime | None = Field(alias="CompleteTime", default=None)
    create_date: datetime | None = Field(alias="CreateTime", default=None)
    meeting_id: int | None = Field(alias="OriginId", default=None)
    meeting_name: str | None = Field(alias="Origin", default=None)
    complete: bool = Field(alias="Complete", default=False)

    @field_validator("due_date", "complete_date", "create_date", mode="before")
    @classmethod
    def parse_optional_datetime(cls, v: Any) -> datetime | None:
        """Parse optional datetime fields.

        Returns:
            The parsed datetime or None if empty.

        """
        if v is None or v == "":
            return None
        return v


class Issue(BloomyBaseModel):
    """Model for issue."""

    id: int = Field(alias="Id")
    name: str = Field(alias="Name")
    details_url: str | None = Field(alias="DetailsUrl", default=None)
    created_date: datetime = Field(alias="CreateDate")
    meeting_id: int = Field(alias="MeetingId")
    meeting_name: str = Field(alias="MeetingName")
    owner_name: str = Field(alias="OwnerName")
    owner_id: int = Field(alias="OwnerId")
    owner_image_url: str = Field(alias="OwnerImageUrl")
    closed_date: datetime | None = Field(alias="ClosedDate", default=None)
    completion_date: datetime | None = Field(alias="CompletionDate", default=None)

    @field_validator("closed_date", "completion_date", mode="before")
    @classmethod
    def parse_optional_datetime(cls, v: Any) -> datetime | None:
        """Parse optional datetime fields.

        Returns:
            The parsed datetime or None if empty.

        """
        if v is None or v == "":
            return None
        return v


class Headline(BloomyBaseModel):
    """Model for headline."""

    id: int = Field(alias="Id")
    title: str = Field(alias="Title")
    notes: str = Field(alias="Notes")
    owner_name: str = Field(alias="OwnerName")
    owner_id: int = Field(alias="OwnerId")
    headline_type: str = Field(alias="HeadlineType")
    create_date: datetime = Field(alias="CreateDate")
    meeting_id: int = Field(alias="MeetingId")
    is_archived: bool = Field(alias="IsArchived")


class Goal(BloomyBaseModel):
    """Model for goal (rock)."""

    id: int = Field(alias="Id")
    name: str = Field(alias="Name")
    due_date: datetime = Field(alias="DueDate")
    complete_date: datetime | None = Field(alias="CompleteDate", default=None)
    create_date: datetime = Field(alias="CreateDate")
    is_archived: bool = Field(alias="IsArchived", default=False)
    percent_complete: float = Field(alias="PercentComplete", default=0.0)
    accountable_user_id: int = Field(alias="AccountableUserId")
    accountable_user_name: str | None = Field(alias="AccountableUserName", default=None)

    @field_validator("complete_date", mode="before")
    @classmethod
    def parse_optional_datetime(cls, v: Any) -> datetime | None:
        """Parse optional datetime fields.

        Returns:
            The parsed datetime or None if empty.

        """
        if v is None or v == "":
            return None
        return v


class ScorecardMetric(BloomyBaseModel):
    """Model for scorecard metric."""

    id: int = Field(alias="Id")
    title: str = Field(alias="Title")
    target: float | None = Field(alias="Target", default=None)
    unit: str | None = Field(alias="Unit", default=None)
    week_number: int = Field(alias="WeekNumber")
    value: float | None = Field(alias="Value", default=None)
    metric_type: str = Field(alias="MetricType")
    accountable_user_id: int = Field(alias="AccountableUserId")
    accountable_user_name: str | None = Field(alias="AccountableUserName", default=None)
    is_inverse: bool = Field(alias="IsInverse", default=False)

    @field_validator("target", "value", mode="before")
    @classmethod
    def parse_optional_float(cls, v: Any) -> float | None:
        """Parse optional float fields.

        Returns:
            The parsed float or None if empty.

        """
        if v is None or v == "":
            return None
        return float(v)


class CurrentWeek(BloomyBaseModel):
    """Model for current week information."""

    week_number: int
    start_date: datetime
    end_date: datetime


class GoalInfo(BloomyBaseModel):
    """Model for goal information."""

    id: int
    user_id: int
    user_name: str
    title: str
    created_at: str
    due_date: str | None
    status: str
    meeting_id: int | None = None
    meeting_title: str | None = None


class ArchivedGoalInfo(BloomyBaseModel):
    """Model for archived goal information."""

    id: int
    title: str
    created_at: str
    due_date: str | None
    status: str


class GoalListResponse(BloomyBaseModel):
    """Model for goal list response with archived goals."""

    active: list[GoalInfo]
    archived: list[ArchivedGoalInfo]


class CreatedGoalInfo(BloomyBaseModel):
    """Model for created goal information."""

    id: int
    user_id: int
    user_name: str
    title: str
    meeting_id: int
    meeting_title: str
    status: str
    created_at: str


class ScorecardWeek(BloomyBaseModel):
    """Model for scorecard week details."""

    id: int
    week_number: int
    week_start: str
    week_end: str


class ScorecardItem(BloomyBaseModel):
    """Model for scorecard items."""

    id: int
    measurable_id: int
    accountable_user_id: int
    title: str
    target: float
    value: float | None = None
    week: str  # Changed from int to str to handle "2024-W25" format
    week_id: int
    updated_at: str | None = None


class IssueDetails(BloomyBaseModel):
    """Model for issue details."""

    id: int
    title: str
    notes_url: str
    created_at: str
    completed_at: str | None = None
    meeting_id: int
    meeting_title: str
    user_id: int
    user_name: str


class IssueListItem(BloomyBaseModel):
    """Model for issue list items."""

    id: int
    title: str
    notes_url: str
    created_at: str
    meeting_id: int
    meeting_title: str | None


class CreatedIssue(BloomyBaseModel):
    """Model for created issue response."""

    id: int
    meeting_id: int
    meeting_title: str
    title: str
    user_id: int
    notes_url: str


class OwnerDetails(BloomyBaseModel):
    """Model for owner details."""

    id: int
    name: str | None = None


class MeetingInfo(BloomyBaseModel):
    """Model for meeting information."""

    id: int
    title: str | None = None


class HeadlineInfo(BloomyBaseModel):
    """Model for headline information."""

    id: int
    title: str
    notes_url: str
    owner_details: OwnerDetails


class HeadlineDetails(BloomyBaseModel):
    """Model for detailed headline information."""

    id: int
    title: str
    notes_url: str
    meeting_details: MeetingInfo
    owner_details: OwnerDetails
    archived: bool
    created_at: str
    closed_at: str | None = None


class HeadlineListItem(BloomyBaseModel):
    """Model for headline list items."""

    id: int
    title: str
    meeting_details: MeetingInfo
    owner_details: OwnerDetails
    archived: bool
    created_at: str
    closed_at: str | None = None


class BulkCreateError(BloomyBaseModel):
    """Error detail for failed bulk creation."""

    index: int
    input_data: dict[str, Any]
    error: str


class BulkCreateResult[T](BloomyBaseModel):
    """Result of a bulk create operation."""

    successful: list[T]
    failed: list[BulkCreateError]
