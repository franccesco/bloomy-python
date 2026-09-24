"""Metric (KPI/scorecard) operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from typing import Any

from ...exceptions import GraphQLError
from ..base import (
    NOTES_FIELDS,
    USER_REF_FIELDS,
    AsyncGraphQLOperations,
    GraphQLOperations,
    TimeInput,
    compact,
    dig_nodes,
    to_timestamp,
    to_utc_datetime,
)
from ..models import Metric, MetricFrequency, MetricRule, MetricScore, MetricUnit

# `id` is not selected: on `meeting.metrics` it is the meeting-link id, while
# `measurableId` is the metric id on every query path.
_METRIC_FIELDS = f"""
measurableId
title
units
rule
frequency
singleGoalValue
minGoalValue
maxGoalValue
archived
dateCreated
isExternallySynced
{NOTES_FIELDS}
{USER_REF_FIELDS}
"""

_METRIC_SCORE_FIELDS = "id value timestamp notesText measurableId"

# A DAILY score is stored at the start of its day, not at the requested time, so
# `set_score()` searches this many seconds either side and matches the UTC day.
_DAILY_SCORE_SEARCH_WINDOW = 2 * 24 * 60 * 60


def _text(value: object) -> str | None:
    """Stringify an enum or decimal input value, as the API expects.

    Returns:
        `str(value)`, or `None` if `value` is `None`.

    """
    return None if value is None else str(value)


class MetricOperationsMixin:
    """GraphQL documents, inputs, and response parsing shared by metric operations."""

    _METRIC_DETAILS_QUERY = f"""
    query($id: Long!) {{
      metric(id: $id) {{
        {_METRIC_FIELDS}
      }}
    }}
    """

    _METRIC_MEETING_LIST_QUERY = f"""
    query($meetingId: Long!, $where: MetricQueryModelFilterInput) {{
      meeting(id: $meetingId) {{
        metrics(where: $where, order: [{{ indexInTable: ASC }}]) {{
          nodes {{
            {_METRIC_FIELDS}
          }}
        }}
      }}
    }}
    """

    _METRIC_USER_LIST_QUERY = f"""
    query($userId: Long!, $where: MetricQueryModelFilterInput) {{
      user(id: $userId) {{
        metrics(where: $where, order: [{{ dateCreated: ASC }}]) {{
          nodes {{
            {_METRIC_FIELDS}
          }}
        }}
      }}
    }}
    """

    _METRIC_CREATE_MUTATION = """
    mutation($input: MetricCreateModelInput!) {
      CreateMetric(input: $input) {
        id
      }
    }
    """

    _METRIC_EDIT_MUTATION = """
    mutation($input: MetricEditModelInput!) {
      EditMetric(input: $input) {
        id
      }
    }
    """

    _METRIC_SCORES_QUERY = f"""
    query($metricId: Long!, $where: MetricScoreQueryModelFilterInput) {{
      metric(id: $metricId) {{
        scoresNonPaginated(where: $where, order: [{{ timestamp: DESC }}]) {{
          {_METRIC_SCORE_FIELDS}
        }}
      }}
    }}
    """

    _METRIC_SCORE_CREATE_MUTATION = """
    mutation($input: MetricScoreCreateModelInput!) {
      CreateMetricScore(input: $input) {
        id
      }
    }
    """

    _METRIC_SCORE_EDIT_MUTATION = """
    mutation($input: MetricScoreEditModelInput!) {
      EditMetricScore(input: $input) {
        id
      }
    }
    """

    @classmethod
    def _metric_list_request(
        cls,
        meeting_id: int | None,
        user_id: int | None,
        *,
        frequency: MetricFrequency | str | None,
    ) -> tuple[str, dict[str, Any]]:
        """Pick the list document for a meeting or a user, with its variables.

        `meeting.metrics` also returns archived metrics and scorecard dividers
        (`metricType: DIVIDER`), so both documents filter them out with `where`.

        Returns:
            The query document and its variables.

        """
        conditions: list[dict[str, Any]] = [
            {"archived": {"eq": False}},
            {"metricType": {"eq": "METRIC"}},
        ]
        if frequency is not None:
            conditions.append({"frequency": {"eq": str(frequency)}})
        where = {"and": conditions}
        if meeting_id is not None:
            return cls._METRIC_MEETING_LIST_QUERY, {
                "meetingId": meeting_id,
                "where": where,
            }
        return cls._METRIC_USER_LIST_QUERY, {"userId": user_id, "where": where}

    @staticmethod
    def _metrics_from(data: dict[str, Any]) -> list[Metric]:
        """Validate the metrics of a meeting or user list response.

        A response carries either `meeting` or `user`; the absent one reads as
        empty.

        Returns:
            The metrics.

        """
        return [
            Metric.model_validate(node)
            for owner in ("meeting", "user")
            for node in dig_nodes(data, owner, "metrics")
        ]

    @staticmethod
    def _metric_goal_conflict(
        rule: MetricRule | str | None,
        goal: float | str | None,
        min_goal: float | str | None,
        max_goal: float | str | None,
    ) -> str | None:
        """Check that the goal fields match the rule.

        `goal` (`singleGoalValue`) is for every rule except `BETWEEN`, and
        `min_goal`/`max_goal` are for `BETWEEN` only. Callers raise the
        `ValueError` themselves so pydoclint can check their docstrings.

        Returns:
            A message describing the conflict, or `None` if there is none.

        """
        has_range_goal = min_goal is not None or max_goal is not None
        if rule is None:
            if goal is not None and has_range_goal:
                return "`goal` cannot be combined with `min_goal`/`max_goal`."
            return None
        is_between = str(rule) == MetricRule.BETWEEN
        if is_between and goal is not None:
            return (
                "`goal` cannot be used with rule=BETWEEN; "
                "use `min_goal`/`max_goal` instead."
            )
        if not is_between and has_range_goal:
            return "`min_goal`/`max_goal` can only be used with rule=BETWEEN."
        return None

    @staticmethod
    def _metric_fields(
        *,
        title: str | None,
        user_id: int | None,
        units: MetricUnit | str | None,
        rule: MetricRule | str | None,
        goal: float | str | None,
        min_goal: float | str | None,
        max_goal: float | str | None,
    ) -> dict[str, Any]:
        """Build the metric fields that were given, apart from notes.

        `MetricEditModelInput` and `MetricCreateModelInput` name these fields
        the same way, so `create()` reuses them.

        Returns:
            The non-`None` input fields.

        """
        return compact(
            title=title,
            assignee=user_id,
            units=_text(units),
            rule=_text(rule),
            singleGoalValue=_text(goal),
            minGoalValue=_text(min_goal),
            maxGoalValue=_text(max_goal),
        )

    @classmethod
    def _metric_create_input(
        cls,
        *,
        meeting_id: int,
        title: str,
        user_id: int,
        units: MetricUnit | str,
        rule: MetricRule | str,
        frequency: MetricFrequency | str,
        goal: float | str | None,
        min_goal: float | str | None,
        max_goal: float | str | None,
    ) -> dict[str, Any]:
        """Build the `MetricCreateModelInput` fields, apart from notes.

        Returns:
            The input fields.

        """
        fields = cls._metric_fields(
            title=title,
            user_id=user_id,
            units=units,
            rule=rule,
            goal=goal,
            min_goal=min_goal,
            max_goal=max_goal,
        )
        return {
            **fields,
            "frequency": str(frequency),
            "averageOverrideType": "NONE",
            "meetings": [meeting_id],
            "customGoals": [],
        }

    @staticmethod
    def _score_create_input(
        metric_id: int, value: float | str, timestamp: float
    ) -> dict[str, Any]:
        """Build the `MetricScoreCreateModelInput` fields.

        Returns:
            The input fields.

        """
        return {"metricId": metric_id, "value": str(value), "timestamp": timestamp}

    @staticmethod
    def _scores_variables(
        metric_id: int,
        start: TimeInput | None,
        end: TimeInput | None,
    ) -> dict[str, Any]:
        """Build the `_METRIC_SCORES_QUERY` variables for a timestamp range.

        Returns:
            The query variables, with a `null` `where` when neither bound is
            given.

        """
        conditions: list[dict[str, Any]] = []
        if start is not None:
            conditions.append({"timestamp": {"gte": to_timestamp(start)}})
        if end is not None:
            conditions.append({"timestamp": {"lte": to_timestamp(end)}})
        return {
            "metricId": metric_id,
            "where": {"and": conditions} if conditions else None,
        }

    @staticmethod
    def _scores_from(data: dict[str, Any], *, include_empty: bool) -> list[MetricScore]:
        """Validate the scores of a `_METRIC_SCORES_QUERY` response.

        `scoresNonPaginated` is a plain list, not a `{ nodes }` connection.

        Returns:
            The scores, without empty placeholders unless `include_empty`.

        """
        metric: dict[str, Any] = data.get("metric") or {}
        nodes: list[dict[str, Any]] = metric.get("scoresNonPaginated") or []
        scores = [MetricScore.model_validate(node) for node in nodes]
        if include_empty:
            return scores
        return [score for score in scores if score.value is not None]

    @classmethod
    def _score_on_day(
        cls, data: dict[str, Any], timestamp: float
    ) -> MetricScore | None:
        """Find the score of a `_METRIC_SCORES_QUERY` response on `timestamp`'s UTC day.

        Returns:
            The first matching score (empty placeholders included), or `None`.

        """
        day = to_utc_datetime(timestamp).date()
        for score in cls._scores_from(data, include_empty=True):
            if score.week_date is not None and score.week_date.date() == day:
                return score
        return None

    @staticmethod
    def _created_score_id(data: dict[str, Any], value: float | str) -> int:
        """Read the new score's id from a `CreateMetricScore` response.

        Returns:
            The score id.

        Raises:
            GraphQLError: If the result is `null`, meaning `value` could not be
                parsed as a decimal number.

        """
        created: dict[str, Any] | None = data.get("CreateMetricScore")
        if created is None:
            raise GraphQLError(
                f"CreateMetricScore: value {value!r} could not be parsed as a number"
            )
        return int(created["id"])

    @staticmethod
    def _is_duplicate_score_error(exc: GraphQLError) -> bool:
        """Check whether `CreateMetricScore` failed because a DAILY score exists.

        `CreateMetricScore` upserts weekly/monthly/quarterly scores by period,
        but for a DAILY metric it raises this error when the day already has a
        score (verified live).

        Returns:
            `True` if any raw error's `extensions.message` says the score
            already exists.

        """
        for error in exc.errors:
            extensions: dict[str, Any] = error.get("extensions") or {}
            if "already exists" in str(extensions.get("message") or "").lower():
                return True
        return False


class MetricOperations(GraphQLOperations, MetricOperationsMixin):
    """Class to handle v2 (GraphQL) operations related to metrics (KPIs).

    Note:
        Archiving a metric cannot be undone through the GraphQL API
        (`EditMetric(archived: false)` does not restore it -- it re-archives
        it). There is no `restore()`.

    """

    def details(self, metric_id: int) -> Metric:
        """Get details for a metric.

        Args:
            metric_id: The ID of the metric (its `measurableId`).

        Returns:
            A `Metric` model instance.

        Example:
            ```python
            client.v2.metric.details(2036155)
            # Returns: Metric(id=2036155, title='New Customers', ...)
            ```

        """
        data = self._execute(self._METRIC_DETAILS_QUERY, {"id": metric_id})
        return Metric.model_validate(
            self._one(data, "metric", label="Metric", entity_id=metric_id)
        )

    def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        frequency: MetricFrequency | str | None = None,
    ) -> builtins.list[Metric]:
        """List metrics for a meeting or a user.

        Args:
            meeting_id: The ID of the meeting. Mutually exclusive with
                `user_id`.
            user_id: The ID of the metric owner. Mutually exclusive with
                `meeting_id`. If neither is given, defaults to the current
                user.
            frequency: If given, only list metrics with this scoring
                frequency.

        Returns:
            A list of `Metric` model instances. Archived metrics and
            scorecard dividers are excluded.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        Example:
            ```python
            client.v2.metric.list(meeting_id=349524)
            # Returns: [Metric(id=2036155, title='New Customers', ...), ...]
            ```

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = self.user_id
        query, variables = self._metric_list_request(
            meeting_id, user_id, frequency=frequency
        )
        return self._metrics_from(self._execute(query, variables))

    def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        goal: float | str | None = None,
        units: MetricUnit | str = MetricUnit.NONE,
        rule: MetricRule | str = MetricRule.GREATER_THAN,
        frequency: MetricFrequency | str = MetricFrequency.WEEKLY,
        min_goal: float | str | None = None,
        max_goal: float | str | None = None,
        notes: str | None = None,
    ) -> Metric:
        """Create a new metric (KPI).

        Args:
            meeting_id: The ID of the meeting to attach the metric to.
            title: The title of the metric.
            user_id: The ID of the metric owner (defaults to the current
                user).
            goal: The single goal value. Use for every `rule` except
                `MetricRule.BETWEEN`; mutually exclusive with `min_goal`/
                `max_goal`.
            units: The display unit for scores.
            rule: The comparison rule between a score and its goal.
            frequency: The scoring cadence.
            min_goal: The lower goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            max_goal: The upper goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            notes: Description text for the metric.

        Returns:
            The newly created `Metric`.

        Raises:
            ValueError: If `goal` is combined with `rule=MetricRule.BETWEEN`,
                or if `min_goal`/`max_goal` is combined with any other rule.

        Example:
            ```python
            client.v2.metric.create(349524, "New Customers", goal=10)
            # Returns: Metric(id=2036155, title='New Customers', ...)
            ```

        """
        conflict = self._metric_goal_conflict(rule, goal, min_goal, max_goal)
        if conflict:
            raise ValueError(conflict)
        if user_id is None:
            user_id = self.user_id
        input_ = self._metric_create_input(
            meeting_id=meeting_id,
            title=title,
            user_id=user_id,
            units=units,
            rule=rule,
            frequency=frequency,
            goal=goal,
            min_goal=min_goal,
            max_goal=max_goal,
        )
        result = self._mutate(
            self._METRIC_CREATE_MUTATION,
            {"input": {**input_, **self._notes_input(notes)}},
            root_field="CreateMetric",
            action="create metric",
        )
        return self.details(result["id"])

    def update(
        self,
        metric_id: int,
        *,
        title: str | None = None,
        user_id: int | None = None,
        goal: float | str | None = None,
        min_goal: float | str | None = None,
        max_goal: float | str | None = None,
        units: MetricUnit | str | None = None,
        rule: MetricRule | str | None = None,
        notes: str | None = None,
    ) -> Metric:
        """Update an existing metric.

        Args:
            metric_id: The ID of the metric to update.
            title: New title for the metric.
            user_id: New owner for the metric.
            goal: New single goal value. Use for every `rule` except
                `MetricRule.BETWEEN`; mutually exclusive with `min_goal`/
                `max_goal`.
            min_goal: New lower goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            max_goal: New upper goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            units: New display unit for scores.
            rule: New comparison rule between a score and its goal.
            notes: New description text for the metric.

        Returns:
            The updated `Metric`.

        Raises:
            ValueError: If no update fields are provided, if `goal` is
                combined with `rule=MetricRule.BETWEEN`, or if `min_goal`/
                `max_goal` is combined with a non-`BETWEEN` `rule`.

        Example:
            ```python
            client.v2.metric.update(2036155, title="New Title")
            # Returns: Metric(id=2036155, title='New Title', ...)
            ```

        """
        fields = self._metric_fields(
            title=title,
            user_id=user_id,
            units=units,
            rule=rule,
            goal=goal,
            min_goal=min_goal,
            max_goal=max_goal,
        )
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        conflict = self._metric_goal_conflict(rule, goal, min_goal, max_goal)
        if conflict:
            raise ValueError(conflict)
        fields.update(self._notes_input(notes))
        return self._edit(metric_id, fields, action="update metric")

    def archive(self, metric_id: int) -> Metric:
        """Archive a metric.

        Note:
            This cannot be undone through the GraphQL API -- there is no
            `restore()` (see the class `Note`).

        Args:
            metric_id: The ID of the metric to archive.

        Returns:
            The updated `Metric`.

        """
        return self._edit(metric_id, {"archived": True}, action="archive metric")

    def scores(
        self,
        metric_id: int,
        *,
        start: TimeInput | None = None,
        end: TimeInput | None = None,
        include_empty: bool = False,
    ) -> builtins.list[MetricScore]:
        """List the scores of a metric.

        Args:
            metric_id: The ID of the metric.
            start: Only include scores at or after this time.
            end: Only include scores at or before this time.
            include_empty: If `True`, also include placeholder rows with no
                value set.

        Returns:
            A list of `MetricScore` model instances, most recent first.

        Example:
            ```python
            client.v2.metric.scores(2036155)
            # Returns: [MetricScore(id=1, value=120.0, ...), ...]
            ```

        """
        variables = self._scores_variables(metric_id, start, end)
        data = self._execute(self._METRIC_SCORES_QUERY, variables)
        return self._scores_from(data, include_empty=include_empty)

    def set_score(
        self,
        metric_id: int,
        value: float | str,
        timestamp: TimeInput,
    ) -> MetricScore:
        """Set a metric's score for a given time.

        For weekly/monthly/quarterly metrics this upserts the score for
        whichever period `timestamp` falls in. For DAILY metrics, a score
        already exists for every day (as an empty placeholder), so this
        looks the existing score up and edits it instead.

        Args:
            metric_id: The ID of the metric.
            value: The score value (a decimal number).
            timestamp: The time the score belongs to, as a `datetime`,
                `date`, or unix timestamp (seconds).

        Returns:
            The written `MetricScore`, re-read after the write.

        Raises:
            GraphQLError: If `value` cannot be parsed as a decimal number.

        Example:
            ```python
            client.v2.metric.set_score(2036155, 120, date(2026, 9, 21))
            # Returns: MetricScore(id=1, value=120.0, ...)
            ```

        """
        ts = to_timestamp(timestamp)
        try:
            data = self._execute(
                self._METRIC_SCORE_CREATE_MUTATION,
                {"input": self._score_create_input(metric_id, value, ts)},
            )
        except GraphQLError as exc:
            if not self._is_duplicate_score_error(exc):
                raise
            variables = self._scores_variables(
                metric_id,
                ts - _DAILY_SCORE_SEARCH_WINDOW,
                ts + _DAILY_SCORE_SEARCH_WINDOW,
            )
            existing = self._score_on_day(
                self._execute(self._METRIC_SCORES_QUERY, variables), ts
            )
            if existing is None:
                raise
            return self.update_score(metric_id, existing.id, value=value)
        return self._read_score(metric_id, self._created_score_id(data, value))

    def update_score(
        self,
        metric_id: int,
        score_id: int,
        *,
        value: float | str | None = None,
        notes: str | None = None,
    ) -> MetricScore:
        """Update an existing metric score's value and/or note.

        Args:
            metric_id: The ID of the score's parent metric, needed to
                re-read it afterwards (there is no root `score(id)` query).
            score_id: The ID of the score to update.
            value: New score value.
            notes: New note text for the score.

        Returns:
            The updated `MetricScore`.

        Raises:
            ValueError: If neither `value` nor `notes` is provided.

        Example:
            ```python
            client.v2.metric.update_score(2036155, 499964609, value=125)
            # Returns: MetricScore(id=499964609, value=125.0, ...)
            ```

        """
        fields = compact(value=_text(value), notesText=notes)
        if not fields:
            raise ValueError("At least one of `value` or `notes` must be provided")
        return self._edit_score(metric_id, score_id, fields, action="update score")

    def clear_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Clear a metric score's value, leaving an empty placeholder.

        Args:
            metric_id: The ID of the score's parent metric, needed to
                re-read it afterwards (there is no root `score(id)` query).
            score_id: The ID of the score to clear.

        Returns:
            The updated `MetricScore`, with `value=None`.

        """
        return self._edit_score(
            metric_id, score_id, {"value": None}, action="clear score"
        )

    def _edit(self, metric_id: int, fields: dict[str, Any], *, action: str) -> Metric:
        """Run `EditMetric` with `fields`, then re-read the metric.

        Returns:
            The updated `Metric`.

        """
        self._mutate(
            self._METRIC_EDIT_MUTATION,
            {"input": {"metricId": metric_id, **fields}},
            root_field="EditMetric",
            action=action,
        )
        return self.details(metric_id)

    def _edit_score(
        self, metric_id: int, score_id: int, fields: dict[str, Any], *, action: str
    ) -> MetricScore:
        """Run `EditMetricScore` with `fields`, then re-read the score.

        Returns:
            The updated `MetricScore`.

        """
        self._mutate(
            self._METRIC_SCORE_EDIT_MUTATION,
            {"input": {"id": score_id, **fields}},
            root_field="EditMetricScore",
            action=action,
        )
        return self._read_score(metric_id, score_id)

    def _read_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Read a single score through its parent metric.

        Returns:
            The `MetricScore` model instance.

        """
        data = self._execute(
            self._METRIC_SCORES_QUERY,
            {"metricId": metric_id, "where": {"id": {"eq": score_id}}},
        )
        return MetricScore.model_validate(
            self._one(
                data,
                "metric",
                "scoresNonPaginated",
                label="Metric score",
                entity_id=score_id,
            )
        )


class AsyncMetricOperations(AsyncGraphQLOperations, MetricOperationsMixin):
    """Async class to handle v2 (GraphQL) operations related to metrics (KPIs).

    Note:
        See `MetricOperations` for why there is no `restore()`.

    """

    async def details(self, metric_id: int) -> Metric:
        """Get details for a metric.

        Args:
            metric_id: The ID of the metric (its `measurableId`).

        Returns:
            A `Metric` model instance.

        """
        data = await self._execute(self._METRIC_DETAILS_QUERY, {"id": metric_id})
        return Metric.model_validate(
            self._one(data, "metric", label="Metric", entity_id=metric_id)
        )

    async def list(
        self,
        meeting_id: int | None = None,
        user_id: int | None = None,
        *,
        frequency: MetricFrequency | str | None = None,
    ) -> builtins.list[Metric]:
        """List metrics for a meeting or a user.

        Args:
            meeting_id: The ID of the meeting. Mutually exclusive with
                `user_id`.
            user_id: The ID of the metric owner. Mutually exclusive with
                `meeting_id`. If neither is given, defaults to the current
                user.
            frequency: If given, only list metrics with this scoring
                frequency.

        Returns:
            A list of `Metric` model instances. Archived metrics and
            scorecard dividers are excluded.

        Raises:
            ValueError: If both `meeting_id` and `user_id` are provided.

        """  # noqa: DOC502
        self._validate_mutual_exclusion(meeting_id, user_id, "meeting_id", "user_id")
        if meeting_id is None and user_id is None:
            user_id = await self.get_user_id()
        query, variables = self._metric_list_request(
            meeting_id, user_id, frequency=frequency
        )
        return self._metrics_from(await self._execute(query, variables))

    async def create(
        self,
        meeting_id: int,
        title: str,
        user_id: int | None = None,
        goal: float | str | None = None,
        units: MetricUnit | str = MetricUnit.NONE,
        rule: MetricRule | str = MetricRule.GREATER_THAN,
        frequency: MetricFrequency | str = MetricFrequency.WEEKLY,
        min_goal: float | str | None = None,
        max_goal: float | str | None = None,
        notes: str | None = None,
    ) -> Metric:
        """Create a new metric (KPI).

        Args:
            meeting_id: The ID of the meeting to attach the metric to.
            title: The title of the metric.
            user_id: The ID of the metric owner (defaults to the current
                user).
            goal: The single goal value. Use for every `rule` except
                `MetricRule.BETWEEN`; mutually exclusive with `min_goal`/
                `max_goal`.
            units: The display unit for scores.
            rule: The comparison rule between a score and its goal.
            frequency: The scoring cadence.
            min_goal: The lower goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            max_goal: The upper goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            notes: Description text for the metric.

        Returns:
            The newly created `Metric`.

        Raises:
            ValueError: If `goal` is combined with `rule=MetricRule.BETWEEN`,
                or if `min_goal`/`max_goal` is combined with any other rule.

        """
        conflict = self._metric_goal_conflict(rule, goal, min_goal, max_goal)
        if conflict:
            raise ValueError(conflict)
        if user_id is None:
            user_id = await self.get_user_id()
        input_ = self._metric_create_input(
            meeting_id=meeting_id,
            title=title,
            user_id=user_id,
            units=units,
            rule=rule,
            frequency=frequency,
            goal=goal,
            min_goal=min_goal,
            max_goal=max_goal,
        )
        result = await self._mutate(
            self._METRIC_CREATE_MUTATION,
            {"input": {**input_, **await self._notes_input(notes)}},
            root_field="CreateMetric",
            action="create metric",
        )
        return await self.details(result["id"])

    async def update(
        self,
        metric_id: int,
        *,
        title: str | None = None,
        user_id: int | None = None,
        goal: float | str | None = None,
        min_goal: float | str | None = None,
        max_goal: float | str | None = None,
        units: MetricUnit | str | None = None,
        rule: MetricRule | str | None = None,
        notes: str | None = None,
    ) -> Metric:
        """Update an existing metric.

        Args:
            metric_id: The ID of the metric to update.
            title: New title for the metric.
            user_id: New owner for the metric.
            goal: New single goal value. Use for every `rule` except
                `MetricRule.BETWEEN`; mutually exclusive with `min_goal`/
                `max_goal`.
            min_goal: New lower goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            max_goal: New upper goal bound. Only valid with
                `rule=MetricRule.BETWEEN`.
            units: New display unit for scores.
            rule: New comparison rule between a score and its goal.
            notes: New description text for the metric.

        Returns:
            The updated `Metric`.

        Raises:
            ValueError: If no update fields are provided, if `goal` is
                combined with `rule=MetricRule.BETWEEN`, or if `min_goal`/
                `max_goal` is combined with a non-`BETWEEN` `rule`.

        """
        fields = self._metric_fields(
            title=title,
            user_id=user_id,
            units=units,
            rule=rule,
            goal=goal,
            min_goal=min_goal,
            max_goal=max_goal,
        )
        if not fields and notes is None:
            raise ValueError("At least one field must be provided for update")
        conflict = self._metric_goal_conflict(rule, goal, min_goal, max_goal)
        if conflict:
            raise ValueError(conflict)
        fields.update(await self._notes_input(notes))
        return await self._edit(metric_id, fields, action="update metric")

    async def archive(self, metric_id: int) -> Metric:
        """Archive a metric.

        Note:
            This cannot be undone through the GraphQL API -- there is no
            `restore()` (see the class `Note`).

        Args:
            metric_id: The ID of the metric to archive.

        Returns:
            The updated `Metric`.

        """
        return await self._edit(metric_id, {"archived": True}, action="archive metric")

    async def scores(
        self,
        metric_id: int,
        *,
        start: TimeInput | None = None,
        end: TimeInput | None = None,
        include_empty: bool = False,
    ) -> builtins.list[MetricScore]:
        """List the scores of a metric.

        Args:
            metric_id: The ID of the metric.
            start: Only include scores at or after this time.
            end: Only include scores at or before this time.
            include_empty: If `True`, also include placeholder rows with no
                value set.

        Returns:
            A list of `MetricScore` model instances, most recent first.

        """
        variables = self._scores_variables(metric_id, start, end)
        data = await self._execute(self._METRIC_SCORES_QUERY, variables)
        return self._scores_from(data, include_empty=include_empty)

    async def set_score(
        self,
        metric_id: int,
        value: float | str,
        timestamp: TimeInput,
    ) -> MetricScore:
        """Set a metric's score for a given time.

        For weekly/monthly/quarterly metrics this upserts the score for
        whichever period `timestamp` falls in. For DAILY metrics, a score
        already exists for every day (as an empty placeholder), so this
        looks the existing score up and edits it instead.

        Args:
            metric_id: The ID of the metric.
            value: The score value (a decimal number).
            timestamp: The time the score belongs to, as a `datetime`,
                `date`, or unix timestamp (seconds).

        Returns:
            The written `MetricScore`, re-read after the write.

        Raises:
            GraphQLError: If `value` cannot be parsed as a decimal number.

        """
        ts = to_timestamp(timestamp)
        try:
            data = await self._execute(
                self._METRIC_SCORE_CREATE_MUTATION,
                {"input": self._score_create_input(metric_id, value, ts)},
            )
        except GraphQLError as exc:
            if not self._is_duplicate_score_error(exc):
                raise
            variables = self._scores_variables(
                metric_id,
                ts - _DAILY_SCORE_SEARCH_WINDOW,
                ts + _DAILY_SCORE_SEARCH_WINDOW,
            )
            existing = self._score_on_day(
                await self._execute(self._METRIC_SCORES_QUERY, variables), ts
            )
            if existing is None:
                raise
            return await self.update_score(metric_id, existing.id, value=value)
        return await self._read_score(metric_id, self._created_score_id(data, value))

    async def update_score(
        self,
        metric_id: int,
        score_id: int,
        *,
        value: float | str | None = None,
        notes: str | None = None,
    ) -> MetricScore:
        """Update an existing metric score's value and/or note.

        Args:
            metric_id: The ID of the score's parent metric, needed to
                re-read it afterwards (there is no root `score(id)` query).
            score_id: The ID of the score to update.
            value: New score value.
            notes: New note text for the score.

        Returns:
            The updated `MetricScore`.

        Raises:
            ValueError: If neither `value` nor `notes` is provided.

        """
        fields = compact(value=_text(value), notesText=notes)
        if not fields:
            raise ValueError("At least one of `value` or `notes` must be provided")
        return await self._edit_score(
            metric_id, score_id, fields, action="update score"
        )

    async def clear_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Clear a metric score's value, leaving an empty placeholder.

        Args:
            metric_id: The ID of the score's parent metric, needed to
                re-read it afterwards (there is no root `score(id)` query).
            score_id: The ID of the score to clear.

        Returns:
            The updated `MetricScore`, with `value=None`.

        """
        return await self._edit_score(
            metric_id, score_id, {"value": None}, action="clear score"
        )

    async def _edit(
        self, metric_id: int, fields: dict[str, Any], *, action: str
    ) -> Metric:
        """Run `EditMetric` with `fields`, then re-read the metric.

        Returns:
            The updated `Metric`.

        """
        await self._mutate(
            self._METRIC_EDIT_MUTATION,
            {"input": {"metricId": metric_id, **fields}},
            root_field="EditMetric",
            action=action,
        )
        return await self.details(metric_id)

    async def _edit_score(
        self, metric_id: int, score_id: int, fields: dict[str, Any], *, action: str
    ) -> MetricScore:
        """Run `EditMetricScore` with `fields`, then re-read the score.

        Returns:
            The updated `MetricScore`.

        """
        await self._mutate(
            self._METRIC_SCORE_EDIT_MUTATION,
            {"input": {"id": score_id, **fields}},
            root_field="EditMetricScore",
            action=action,
        )
        return await self._read_score(metric_id, score_id)

    async def _read_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Read a single score through its parent metric.

        Returns:
            The `MetricScore` model instance.

        """
        data = await self._execute(
            self._METRIC_SCORES_QUERY,
            {"metricId": metric_id, "where": {"id": {"eq": score_id}}},
        )
        return MetricScore.model_validate(
            self._one(
                data,
                "metric",
                "scoresNonPaginated",
                label="Metric score",
                entity_id=score_id,
            )
        )
