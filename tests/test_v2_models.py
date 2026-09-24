"""Tests for the v2 (GraphQL) model base behaviour."""

from __future__ import annotations

from datetime import UTC, datetime

from bloomy.v2.models import (
    Goal,
    Headline,
    Issue,
    Meeting,
    Metric,
    MetricScore,
    User,
)

NOTES = {
    "notesId": "pad-1",
    "notesText": "pad text\n",
    "localHtml": None,
    "collaborationEnabled": True,
}


class TestGqlBaseModel:
    """Tests for alias/name validation and the notes fill."""

    def test_alias_takes_precedence_over_field_name(self) -> None:
        """The aliased key wins when a raw key is also named like the field.

        On `meeting(id){ metrics }` the raw `id` is a meeting-link id, not the
        metric id (`measurableId`).
        """
        metric = Metric.model_validate(
            {
                "id": 111,
                "measurableId": 2036155,
                "units": "NONE",
                "rule": "GREATER_THAN",
                "frequency": "WEEKLY",
                "dateCreated": 1790000000,
            }
        )

        assert metric.id == 2036155

    def test_fills_notes_from_pad_text(self) -> None:
        """`notes` comes from `notesText` when collaboration is enabled."""
        headline = Headline.model_validate(
            {"id": 1, "dateCreated": 1790000000, **NOTES}
        )

        assert headline.notes == "pad text"
        assert headline.notes_id == "pad-1"

    def test_fills_notes_from_local_html(self) -> None:
        """Without collaboration, `notes` is the tag-stripped `localHtml`."""
        headline = Headline.model_validate(
            {
                "id": 1,
                "dateCreated": 1790000000,
                **NOTES,
                "collaborationEnabled": False,
                "localHtml": "<p>a &amp; b</p>",
            }
        )

        assert headline.notes == "a & b"

    def test_datetimes_are_utc(self) -> None:
        """Unix-seconds timestamps become aware UTC datetimes."""
        headline = Headline.model_validate({"id": 1, "dateCreated": 0})

        assert headline.created_date == datetime(1970, 1, 1, tzinfo=UTC)

    def test_model_dump_round_trips(self) -> None:
        """`model_validate(model_dump())` rebuilds an equal model."""
        issue = Issue.model_validate(
            {
                "id": 1,
                "addToDepartmentPlan": True,
                "archived": True,
                "dateCreated": 1790000000,
                "assignee": {"id": 3, "fullName": "Fran Orozco"},
                **NOTES,
            }
        )
        score = MetricScore.model_validate(
            {"id": 5, "measurableId": 9, "value": "12.5", "notesText": "note"}
        )

        assert Issue.model_validate(issue.model_dump()) == issue
        assert Issue.model_validate(issue.model_dump(by_alias=True)) == issue
        assert MetricScore.model_validate(score.model_dump()) == score

    def test_assignment_keeps_working(self) -> None:
        """Field assignment is still validated by field name."""
        headline = Headline.model_validate({"id": 1, "dateCreated": 0, **NOTES})
        headline.archived = True

        assert headline.archived is True
        assert headline.notes == "pad text"


class TestConnections:
    """Tests for nested `{nodes}` connections."""

    def test_meeting_attendees_unwrap_nodes_and_nested_email(self) -> None:
        """`attendees { nodes }` validates directly, reading `user { email }`."""
        meeting = Meeting.model_validate(
            {
                "id": 349524,
                "createdTimestamp": 1790000000,
                "attendees": {
                    "nodes": [
                        {"id": 1, "fullName": "A", "user": {"email": "a@x.com"}},
                        {"id": 2, "fullName": "B", "user": None},
                    ]
                },
            }
        )

        assert [user.email for user in meeting.attendees] == ["a@x.com", None]

    def test_goal_connections(self) -> None:
        """`milestones`/`meetings` connections unwrap, and `null` becomes `[]`."""
        goal = Goal.model_validate(
            {
                "id": 5,
                "dateCreated": 1790000000,
                "milestones": None,
                "meetings": {"nodes": [{"id": 349524, "name": "v2 API"}]},
            }
        )

        assert goal.milestones == []
        assert [meeting.id for meeting in goal.meetings] == [349524]

    def test_connection_accepts_plain_list(self) -> None:
        """A connection field given as a plain list validates unchanged."""
        goal = Goal.model_validate(
            {
                "id": 5,
                "dateCreated": 1790000000,
                "meetings": [{"id": 349524, "name": "v2 API"}],
            }
        )

        assert [meeting.name for meeting in goal.meetings] == ["v2 API"]

    def test_user_email_flat(self) -> None:
        """A flat `email` (from `user(id)`) is read as-is."""
        assert User.model_validate({"id": 1, "email": "a@x.com"}).email == "a@x.com"


class TestIssueLongTerm:
    """Tests for the `Issue` long-term/archived rule."""

    def test_long_term_issue_is_not_archived(self) -> None:
        """The API's `archived: true` on a long-term issue is not reported."""
        issue = Issue.model_validate(
            {
                "id": 1,
                "dateCreated": 1790000000,
                "archived": True,
                "addToDepartmentPlan": True,
            }
        )

        assert issue.long_term is True
        assert issue.archived is False

    def test_short_term_archived_issue_is_archived(self) -> None:
        """A short-term archived issue stays archived."""
        issue = Issue.model_validate(
            {
                "id": 1,
                "dateCreated": 1790000000,
                "archived": True,
                "addToDepartmentPlan": False,
            }
        )

        assert issue.archived is True


class TestMetricScoreNotes:
    """Tests for `MetricScore.notes`, read from the score's own `notesText`."""

    def test_notes_text(self) -> None:
        """`notesText` becomes `notes`, and an empty one becomes `None`."""
        base = {"id": 1, "measurableId": 2, "timestamp": 1790000000}

        assert MetricScore.model_validate({**base, "notesText": "n"}).notes == "n"
        assert MetricScore.model_validate({**base, "notesText": ""}).notes is None
        assert MetricScore.model_validate(base).notes is None
