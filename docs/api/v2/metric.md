# Metric Operations (v2)

GraphQL operations for managing metrics (KPIs) and their scores. See the
[v2 guide](../../guide/v2-graphql-api.md) for how `client.v2` relates to
`client.v1`/`client.scorecard`, and for
[metric score/week semantics](../../guide/v2-graphql-api.md#metric-scores-and-week-semantics).

## API Reference

::: bloomy.v2.operations.metric.MetricOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncMetricOperations` provides the same methods as above, but with async/await support:

::: bloomy.v2.operations.metric.AsyncMetricOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      members: false
      show_bases: false
      show_inheritance_diagram: false

!!! info "Async Usage"
    All methods have the same parameters and return types as their sync counterparts. Simply add `await` before each method call.

## Usage Examples

=== "Sync"

    ```python
    from datetime import date
    from bloomy import Client
    from bloomy.v2.models import MetricRule, MetricUnit, MetricFrequency

    with Client(api_key="your-api-key") as client:
        # Create a metric with a single goal value
        metric = client.v2.metric.create(
            meeting_id=123,
            title="New Customers",
            goal=10,
            units=MetricUnit.NONE,
            rule=MetricRule.GREATER_THAN,
            frequency=MetricFrequency.WEEKLY,
        )

        # Create a BETWEEN-rule metric (min_goal/max_goal instead of goal)
        team_size = client.v2.metric.create(
            meeting_id=123,
            title="Team Size",
            min_goal=5,
            max_goal=10,
            rule=MetricRule.BETWEEN,
        )

        # List metrics for a meeting
        meeting_metrics = client.v2.metric.list(meeting_id=123)

        # Filter by frequency
        weekly_metrics = client.v2.metric.list(meeting_id=123, frequency=MetricFrequency.WEEKLY)

        # Set this week's score
        score = client.v2.metric.set_score(metric.id, 12, date(2026, 9, 21))

        # Update the score's value and/or note
        updated_score = client.v2.metric.update_score(metric.id, score.id, value=14)

        # List scores, most recent first
        scores = client.v2.metric.scores(metric.id)

        # Clear a score back to an empty placeholder
        client.v2.metric.clear_score(metric.id, score.id)

        # Archive (there is no restore for metrics)
        client.v2.metric.archive(metric.id)
    ```

=== "Async"

    ```python
    import asyncio
    from datetime import date
    from bloomy import AsyncClient
    from bloomy.v2.models import MetricRule

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Create a metric with a single goal value
            metric = await client.v2.metric.create(
                meeting_id=123, title="New Customers", goal=10
            )

            # Set this week's score
            score = await client.v2.metric.set_score(metric.id, 12, date(2026, 9, 21))

            # List scores, most recent first
            scores = await client.v2.metric.scores(metric.id)

            # Archive (there is no restore for metrics)
            await client.v2.metric.archive(metric.id)

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `details()` | Get a metric | `metric_id` | `Metric` |
| `list()` | List metrics for a meeting or a user | `meeting_id`, `user_id`, `frequency` | `list[Metric]` |
| `create()` | Create a metric | `meeting_id`, `title`, `user_id`, `goal`, `units`, `rule`, `frequency`, `min_goal`, `max_goal`, `notes` | `Metric` |
| `update()` | Update a metric | `metric_id`, `title`, `user_id`, `goal`, `min_goal`, `max_goal`, `units`, `rule`, `notes` | `Metric` |
| `archive()` | Archive a metric (no `restore()`) | `metric_id` | `Metric` |
| `scores()` | List a metric's scores | `metric_id`, `start`, `end`, `include_empty` | `list[MetricScore]` |
| `set_score()` | Set a score for a given time | `metric_id`, `value`, `timestamp` | `MetricScore` |
| `update_score()` | Update an existing score's value/note | `metric_id`, `score_id`, `value`, `notes` | `MetricScore` |
| `clear_score()` | Clear a score's value | `metric_id`, `score_id` | `MetricScore` |

!!! warning "No `restore()`"
    Archiving a metric is effectively permanent through this SDK — the
    GraphQL API does not support un-archiving one. See
    [Archive vs. delete semantics](../../guide/v2-graphql-api.md#archive-vs-delete-semantics-per-entity)
    in the v2 guide.

!!! note "`goal` vs. `min_goal`/`max_goal`"
    `goal` is for every `rule` except `MetricRule.BETWEEN`; `min_goal`/
    `max_goal` are for `BETWEEN` only. Combining them across that split raises
    `ValueError` locally, before any request is sent.

!!! note "Filtering and update requirements"
    `list()` accepts either `meeting_id` or `user_id`, not both — passing
    both raises `ValueError`. `update()` requires at least one field, or it
    raises `ValueError`. `update_score()` requires at least one of `value` or
    `notes`.
