"""Metric (KPI/scorecard) operations for the Bloomy v2 (GraphQL) API."""

from __future__ import annotations

import builtins
from datetime import UTC, date, datetime
from typing import Any

from ...exceptions import GraphQLError
from ..base import AsyncGraphQLOperations, GraphQLOperations, dig_nodes, extract_notes
from ..models import Metric, MetricFrequency, MetricRule, MetricScore, MetricUnit

# Deliberately does NOT select `id`: on `meeting(id){ metrics }` that field is
# the meeting-link id (`L10Recurrence_Measurable`), not the metric id, so
# selecting it risks the raw dict's `id` key shadowing `measurableId` when
# spread into `Metric(**data)` (both map to the model's aliased `id` field
# under `validate_by_name=True`). `measurableId` alone is always the real
# metric id, on every query path (`metric(id)`, `meeting.metrics`,
# `user.metrics`).
_METRIC_FIELDS = """
measurableId
title
units
rule
frequency
singleGoalValue
minGoalValue
maxGoalValue
archived
metricType
notesId
notesText
localHtml
collaborationEnabled
dateCreated
isExternallySynced
assignee { id fullName }
"""

_METRIC_SCORE_FIELDS = "id value timestamp notesText measurableId"


class MetricOperationsMixin:
    """Shared GraphQL documents and response transforms for metric operations."""

    _METRIC_DETAILS_QUERY = f"""
    query($id: Long!) {{
      metric(id: $id) {{
        {_METRIC_FIELDS}
      }}
    }}
    """

    # `meeting.metrics` also returns metric-divider rows (`metricType:
    # DIVIDER`, `measurableId: 0`) mixed in with real metrics; the `where`
    # filter excludes them server-side (and archived rows, which this
    # connection does not exclude on its own, unlike `user.metrics`).
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

    # `user(id){ metrics }` already excludes archived/deleted metrics
    # server-side; the `archived` filter is kept for parity with the
    # meeting-scoped query above.
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

    # CreateMetric/EditMetric return only `IdModel { id }` (verified live
    # against production), not the `{success message errorDetails}` shape
    # `_run_mutation` expects. A failed create/edit raises through the
    # standard `errors` array instead, so these are executed with plain
    # `_execute`.
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

    # `scoresNonPaginated` is a plain list, not a `{ nodes }` connection
    # (unlike every other list field in the v2 API), so it is read directly
    # rather than through `dig_nodes`.
    _METRIC_SCORES_QUERY = f"""
    query($metricId: Long!, $where: MetricScoreQueryModelFilterInput) {{
      metric(id: $metricId) {{
        scoresNonPaginated(where: $where, order: [{{ timestamp: DESC }}]) {{
          {_METRIC_SCORE_FIELDS}
        }}
      }}
    }}
    """

    # CreateMetricScore/EditMetricScore also return `IdModel { id }`.
    # CreateMetricScore additionally returns `{"CreateMetricScore": null}`
    # with no `errors` entry when `value` cannot be parsed as a decimal
    # (verified live) -- `set_score()` checks for that explicitly.
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

    @staticmethod
    def _metric_where(*, frequency: MetricFrequency | str | None) -> dict[str, Any]:
        """Build the `where` filter shared by both metric list connections.

        Returns:
            A `MetricQueryModelFilterInput`-shaped dictionary.

        """
        conditions: list[dict[str, Any]] = [
            {"archived": {"eq": False}},
            {"metricType": {"eq": "METRIC"}},
        ]
        if frequency is not None:
            conditions.append({"frequency": {"eq": str(frequency)}})
        return {"and": conditions}

    @staticmethod
    def _metric_score_where(
        start_ts: float | None, end_ts: float | None
    ) -> dict[str, Any] | None:
        """Build the `where` filter for a score timestamp range.

        Returns:
            A `MetricScoreQueryModelFilterInput`-shaped dictionary, or `None`
            if neither bound is given (no filtering).

        """
        conditions: list[dict[str, Any]] = []
        if start_ts is not None:
            conditions.append({"timestamp": {"gte": start_ts}})
        if end_ts is not None:
            conditions.append({"timestamp": {"lte": end_ts}})
        return {"and": conditions} if conditions else None

    @staticmethod
    def _metric_goal_conflict(
        rule: MetricRule | str | None,
        goal: float | str | None,
        min_goal: float | str | None,
        max_goal: float | str | None,
    ) -> str | None:
        """Check that goal fields match the BETWEEN/non-BETWEEN rule split.

        `singleGoalValue` (`goal`) and `minGoalValue`/`maxGoalValue`
        (`min_goal`/`max_goal`) are mutually exclusive server-side: `goal` is
        for every rule except `BETWEEN`, and `min_goal`/`max_goal` are for
        `BETWEEN` only. Each caller raises `ValueError` itself (so pydoclint
        can see the `raise` and check the docstring), using this to build the
        message.

        Returns:
            A message describing the conflict, or `None` if the fields are
            consistent.

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
    def _metric_update_fields(
        *,
        title: str | None,
        user_id: int | None,
        units: MetricUnit | str | None,
        rule: MetricRule | str | None,
        goal: float | str | None,
        min_goal: float | str | None,
        max_goal: float | str | None,
    ) -> dict[str, Any]:
        """Build the non-`None` `EditMetric` fields shared by `update()`.

        Returns:
            A dict of `MetricEditModelInput` fields (excluding `metricId` and
            the notes fields, which `update()` sets separately).

        """
        fields: dict[str, Any] = {}
        if title is not None:
            fields["title"] = title
        if user_id is not None:
            fields["assignee"] = user_id
        for key, value in (
            ("units", units),
            ("rule", rule),
            ("singleGoalValue", goal),
            ("minGoalValue", min_goal),
            ("maxGoalValue", max_goal),
        ):
            if value is not None:
                fields[key] = str(value)
        return fields

    @staticmethod
    def _is_duplicate_score_error(exc: GraphQLError) -> bool:
        """Check whether a `GraphQLError` is the DAILY "already exists" error.

        `CreateMetricScore` upserts weekly/monthly/quarterly scores by
        period, but a DAILY score throws this error instead when one already
        exists for the same day (verified live); `set_score()` falls back to
        `EditMetricScore` in that case.

        Returns:
            `True` if any raw error's `extensions.message` reports an
            existing score for the same metric and date.

        """
        for error in exc.errors:
            extensions: dict[str, Any] = error.get("extensions") or {}
            message = str(extensions.get("message") or "")
            if "already exists" in message.lower():
                return True
        return False

    @staticmethod
    def _scores_from(data: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        """Read the `scoresNonPaginated` list out of a metric query's `data`.

        Returns:
            The raw score nodes, or an empty list if the metric was missing.

        """
        metric: dict[str, Any] = data.get("metric") or {}
        return list(metric.get("scoresNonPaginated") or [])

    @staticmethod
    def _same_day(timestamp: float, target: date) -> bool:
        """Check whether a unix-seconds timestamp falls on `target` (UTC).

        Returns:
            `True` if `timestamp`'s UTC calendar date equals `target`.

        """
        return datetime.fromtimestamp(timestamp, tz=UTC).date() == target

    def _transform_metric(self, data: dict[str, Any]) -> Metric:
        """Transform a raw GraphQL metric object into a `Metric` model.

        Returns:
            A `Metric` model instance.

        """
        return Metric(**data, notes=extract_notes(data))

    def _transform_score(self, data: dict[str, Any]) -> MetricScore:
        """Transform a raw GraphQL metric-score object into a `MetricScore` model.

        Scores carry a plain `notesText` note (no Etherpad pad, unlike
        metrics themselves), so this reads it directly rather than through
        `extract_notes`.

        Returns:
            A `MetricScore` model instance.

        """
        return MetricScore(**data, notes=data.get("notesText") or None)


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
        return self._transform_metric(
            self._require_entity(data, "metric", metric_id, "Metric")
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

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        where = self._metric_where(frequency=frequency)

        if meeting_id is not None:
            data = self._execute(
                self._METRIC_MEETING_LIST_QUERY,
                {"meetingId": meeting_id, "where": where},
            )
            nodes = dig_nodes(data, "meeting", "metrics")
        else:
            if user_id is None:
                user_id = self.user_id
            data = self._execute(
                self._METRIC_USER_LIST_QUERY, {"userId": user_id, "where": where}
            )
            nodes = dig_nodes(data, "user", "metrics")

        return [
            self._transform_metric(node)
            for node in nodes
            if node.get("metricType") != "DIVIDER"
        ]

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

        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "units": str(units),
            "rule": str(rule),
            "frequency": str(frequency),
            "averageOverrideType": "NONE",
            "meetings": [meeting_id],
            "customGoals": [],
        }
        if goal is not None:
            input_["singleGoalValue"] = str(goal)
        if min_goal is not None:
            input_["minGoalValue"] = str(min_goal)
        if max_goal is not None:
            input_["maxGoalValue"] = str(max_goal)
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = self._execute(self._METRIC_CREATE_MUTATION, {"input": input_})
        metric_id = self._require_created_id(data.get("CreateMetric"), label="metric")
        return self.details(metric_id)

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
        if all(
            field is None
            for field in (title, user_id, goal, min_goal, max_goal, units, rule, notes)
        ):
            raise ValueError("At least one field must be provided for update")

        conflict = self._metric_goal_conflict(rule, goal, min_goal, max_goal)
        if conflict:
            raise ValueError(conflict)

        input_: dict[str, Any] = {
            "metricId": metric_id,
            **self._metric_update_fields(
                title=title,
                user_id=user_id,
                units=units,
                rule=rule,
                goal=goal,
                min_goal=min_goal,
                max_goal=max_goal,
            ),
        }
        if notes is not None:
            input_["notesId"] = self._create_note(notes)
            input_["collaborationEnabled"] = True

        self._execute(self._METRIC_EDIT_MUTATION, {"input": input_})
        return self.details(metric_id)

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
        self._execute(
            self._METRIC_EDIT_MUTATION,
            {"input": {"metricId": metric_id, "archived": True}},
        )
        return self.details(metric_id)

    def scores(
        self,
        metric_id: int,
        *,
        start: datetime | date | float | int | None = None,
        end: datetime | date | float | int | None = None,
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
        start_ts = self._to_timestamp(start) if start is not None else None
        end_ts = self._to_timestamp(end) if end is not None else None
        where = self._metric_score_where(start_ts, end_ts)

        data = self._execute(
            self._METRIC_SCORES_QUERY, {"metricId": metric_id, "where": where}
        )
        nodes = self._scores_from(data)
        if not include_empty:
            nodes = [node for node in nodes if node.get("value") not in (None, "")]
        return [self._transform_score(node) for node in nodes]

    def set_score(
        self,
        metric_id: int,
        value: float | str,
        timestamp: datetime | date | float | int,
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
        ts = self._to_timestamp(timestamp)
        try:
            data = self._execute(
                self._METRIC_SCORE_CREATE_MUTATION,
                {
                    "input": {
                        "metricId": metric_id,
                        "value": str(value),
                        "timestamp": ts,
                    }
                },
            )
        except GraphQLError as exc:
            if not self._is_duplicate_score_error(exc):
                raise
            existing = self._find_score_for_day(metric_id, ts)
            if existing is None:
                raise
            return self.update_score(metric_id, existing.id, value=value)

        result = data.get("CreateMetricScore")
        if result is None:
            raise GraphQLError(
                f"CreateMetricScore: value {value!r} could not be parsed as a number"
            )
        return self._read_score(metric_id, result["id"])

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
        if value is None and notes is None:
            raise ValueError("At least one of `value` or `notes` must be provided")

        input_: dict[str, Any] = {"id": score_id}
        if value is not None:
            input_["value"] = str(value)
        if notes is not None:
            input_["notesText"] = notes

        self._execute(self._METRIC_SCORE_EDIT_MUTATION, {"input": input_})
        return self._read_score(metric_id, score_id)

    def clear_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Clear a metric score's value, leaving an empty placeholder.

        Args:
            metric_id: The ID of the score's parent metric, needed to
                re-read it afterwards (there is no root `score(id)` query).
            score_id: The ID of the score to clear.

        Returns:
            The updated `MetricScore`, with `value=None`.

        """
        self._execute(
            self._METRIC_SCORE_EDIT_MUTATION, {"input": {"id": score_id, "value": None}}
        )
        return self._read_score(metric_id, score_id)

    def _read_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Re-read a single score through its parent metric.

        Returns:
            The `MetricScore` model instance.

        Raises:
            GraphQLError: If the score is not found under the metric.

        """
        data = self._execute(
            self._METRIC_SCORES_QUERY,
            {"metricId": metric_id, "where": {"and": [{"id": {"eq": score_id}}]}},
        )
        for node in self._scores_from(data):
            if node.get("id") == score_id:
                return self._transform_score(node)
        raise GraphQLError(f"score {score_id} not found under metric {metric_id}")

    def _find_score_for_day(self, metric_id: int, ts: float) -> MetricScore | None:
        """Find the pre-existing score whose UTC calendar day matches `ts`.

        Used by `set_score()` to fall back to `EditMetricScore` for DAILY
        metrics, where a placeholder score already exists for every day.

        Returns:
            The matching `MetricScore`, or `None` if not found.

        """
        target = datetime.fromtimestamp(ts, tz=UTC).date()
        where = self._metric_score_where(ts - 172800, ts + 172800)
        data = self._execute(
            self._METRIC_SCORES_QUERY, {"metricId": metric_id, "where": where}
        )
        for node in self._scores_from(data):
            node_ts = node.get("timestamp")
            if node_ts is not None and self._same_day(node_ts, target):
                return self._transform_score(node)
        return None


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
        return self._transform_metric(
            self._require_entity(data, "metric", metric_id, "Metric")
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

        """
        if meeting_id is not None and user_id is not None:
            raise ValueError("Please provide either meeting_id or user_id, not both.")

        where = self._metric_where(frequency=frequency)

        if meeting_id is not None:
            data = await self._execute(
                self._METRIC_MEETING_LIST_QUERY,
                {"meetingId": meeting_id, "where": where},
            )
            nodes = dig_nodes(data, "meeting", "metrics")
        else:
            if user_id is None:
                user_id = await self.get_user_id()
            data = await self._execute(
                self._METRIC_USER_LIST_QUERY, {"userId": user_id, "where": where}
            )
            nodes = dig_nodes(data, "user", "metrics")

        return [
            self._transform_metric(node)
            for node in nodes
            if node.get("metricType") != "DIVIDER"
        ]

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

        input_: dict[str, Any] = {
            "title": title,
            "assignee": user_id,
            "units": str(units),
            "rule": str(rule),
            "frequency": str(frequency),
            "averageOverrideType": "NONE",
            "meetings": [meeting_id],
            "customGoals": [],
        }
        if goal is not None:
            input_["singleGoalValue"] = str(goal)
        if min_goal is not None:
            input_["minGoalValue"] = str(min_goal)
        if max_goal is not None:
            input_["maxGoalValue"] = str(max_goal)
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        data = await self._execute(self._METRIC_CREATE_MUTATION, {"input": input_})
        metric_id = self._require_created_id(data.get("CreateMetric"), label="metric")
        return await self.details(metric_id)

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
        if all(
            field is None
            for field in (title, user_id, goal, min_goal, max_goal, units, rule, notes)
        ):
            raise ValueError("At least one field must be provided for update")

        conflict = self._metric_goal_conflict(rule, goal, min_goal, max_goal)
        if conflict:
            raise ValueError(conflict)

        input_: dict[str, Any] = {
            "metricId": metric_id,
            **self._metric_update_fields(
                title=title,
                user_id=user_id,
                units=units,
                rule=rule,
                goal=goal,
                min_goal=min_goal,
                max_goal=max_goal,
            ),
        }
        if notes is not None:
            input_["notesId"] = await self._create_note(notes)
            input_["collaborationEnabled"] = True

        await self._execute(self._METRIC_EDIT_MUTATION, {"input": input_})
        return await self.details(metric_id)

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
        await self._execute(
            self._METRIC_EDIT_MUTATION,
            {"input": {"metricId": metric_id, "archived": True}},
        )
        return await self.details(metric_id)

    async def scores(
        self,
        metric_id: int,
        *,
        start: datetime | date | float | int | None = None,
        end: datetime | date | float | int | None = None,
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
        start_ts = self._to_timestamp(start) if start is not None else None
        end_ts = self._to_timestamp(end) if end is not None else None
        where = self._metric_score_where(start_ts, end_ts)

        data = await self._execute(
            self._METRIC_SCORES_QUERY, {"metricId": metric_id, "where": where}
        )
        nodes = self._scores_from(data)
        if not include_empty:
            nodes = [node for node in nodes if node.get("value") not in (None, "")]
        return [self._transform_score(node) for node in nodes]

    async def set_score(
        self,
        metric_id: int,
        value: float | str,
        timestamp: datetime | date | float | int,
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
        ts = self._to_timestamp(timestamp)
        try:
            data = await self._execute(
                self._METRIC_SCORE_CREATE_MUTATION,
                {
                    "input": {
                        "metricId": metric_id,
                        "value": str(value),
                        "timestamp": ts,
                    }
                },
            )
        except GraphQLError as exc:
            if not self._is_duplicate_score_error(exc):
                raise
            existing = await self._find_score_for_day(metric_id, ts)
            if existing is None:
                raise
            return await self.update_score(metric_id, existing.id, value=value)

        result = data.get("CreateMetricScore")
        if result is None:
            raise GraphQLError(
                f"CreateMetricScore: value {value!r} could not be parsed as a number"
            )
        return await self._read_score(metric_id, result["id"])

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
        if value is None and notes is None:
            raise ValueError("At least one of `value` or `notes` must be provided")

        input_: dict[str, Any] = {"id": score_id}
        if value is not None:
            input_["value"] = str(value)
        if notes is not None:
            input_["notesText"] = notes

        await self._execute(self._METRIC_SCORE_EDIT_MUTATION, {"input": input_})
        return await self._read_score(metric_id, score_id)

    async def clear_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Clear a metric score's value, leaving an empty placeholder.

        Args:
            metric_id: The ID of the score's parent metric, needed to
                re-read it afterwards (there is no root `score(id)` query).
            score_id: The ID of the score to clear.

        Returns:
            The updated `MetricScore`, with `value=None`.

        """
        await self._execute(
            self._METRIC_SCORE_EDIT_MUTATION, {"input": {"id": score_id, "value": None}}
        )
        return await self._read_score(metric_id, score_id)

    async def _read_score(self, metric_id: int, score_id: int) -> MetricScore:
        """Re-read a single score through its parent metric.

        Returns:
            The `MetricScore` model instance.

        Raises:
            GraphQLError: If the score is not found under the metric.

        """
        data = await self._execute(
            self._METRIC_SCORES_QUERY,
            {"metricId": metric_id, "where": {"and": [{"id": {"eq": score_id}}]}},
        )
        for node in self._scores_from(data):
            if node.get("id") == score_id:
                return self._transform_score(node)
        raise GraphQLError(f"score {score_id} not found under metric {metric_id}")

    async def _find_score_for_day(
        self, metric_id: int, ts: float
    ) -> MetricScore | None:
        """Find the pre-existing score whose UTC calendar day matches `ts`.

        Used by `set_score()` to fall back to `EditMetricScore` for DAILY
        metrics, where a placeholder score already exists for every day.

        Returns:
            The matching `MetricScore`, or `None` if not found.

        """
        target = datetime.fromtimestamp(ts, tz=UTC).date()
        where = self._metric_score_where(ts - 172800, ts + 172800)
        data = await self._execute(
            self._METRIC_SCORES_QUERY, {"metricId": metric_id, "where": where}
        )
        for node in self._scores_from(data):
            node_ts = node.get("timestamp")
            if node_ts is not None and self._same_day(node_ts, target):
                return self._transform_score(node)
        return None
