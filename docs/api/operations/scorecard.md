# Scorecard Operations

Operations for managing scorecard and scorecard-related data.

## API Reference

::: bloomy.operations.scorecard.ScorecardOperations
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

## Async Version

The async version `AsyncScorecardOperations` provides the same methods as above, but with async/await support:

::: bloomy.operations.async_.scorecard.AsyncScorecardOperations
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
    from bloomy import Client

    with Client(api_key="your-api-key") as client:
        # Get current week information
        week = client.scorecard.current_week()
        print(f"Week {week.week_number}: {week.week_start} to {week.week_end}")

        # List scorecards for current user
        scorecards = client.scorecard.list()
        for s in scorecards:
            print(f"{s.title}: {s.value}/{s.target}")

        # Get a specific scorecard item
        item = client.scorecard.get(measurable_id=123)
        if item:
            print(f"{item.title}: {item.value}/{item.target}")

        # Get from a specific week
        item = client.scorecard.get(measurable_id=123, week_offset=-1)

        # List scorecards for a specific meeting
        meeting_scorecards = client.scorecard.list(meeting_id=123)

        # Include empty values
        all_scorecards = client.scorecard.list(show_empty=True)

        # Get scorecards for previous week
        last_week = client.scorecard.list(week_offset=-1)

        # Update a score for current week
        client.scorecard.score(measurable_id=301, score=95.5)

        # Update score for next week
        client.scorecard.score(
            measurable_id=301,
            score=100,
            week_offset=1
        )
    ```

=== "Async"

    ```python
    import asyncio
    from bloomy import AsyncClient

    async def main():
        async with AsyncClient(api_key="your-api-key") as client:
            # Get current week information
            week = await client.scorecard.current_week()
            print(f"Week {week.week_number}: {week.week_start} to {week.week_end}")

            # List scorecards for current user
            scorecards = await client.scorecard.list()
            for s in scorecards:
                print(f"{s.title}: {s.value}/{s.target}")

            # Get a specific scorecard item
            item = await client.scorecard.get(measurable_id=123)
            if item:
                print(f"{item.title}: {item.value}/{item.target}")

            # Get from a specific week
            item = await client.scorecard.get(measurable_id=123, week_offset=-1)

            # List scorecards for a specific meeting
            meeting_scorecards = await client.scorecard.list(meeting_id=123)

            # Include empty values
            all_scorecards = await client.scorecard.list(show_empty=True)

            # Get scorecards for previous week
            last_week = await client.scorecard.list(week_offset=-1)

            # Update a score for current week
            await client.scorecard.score(measurable_id=301, score=95.5)

            # Update score for next week
            await client.scorecard.score(
                measurable_id=301,
                score=100,
                week_offset=1
            )

    asyncio.run(main())
    ```

## Available Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `current_week()` | Get current week details | - |
| `get()` | Get a single scorecard item | `measurable_id`, `user_id`, `week_offset` |
| `list()` | Get scorecards | `user_id`, `meeting_id`, `show_empty`, `week_offset` |
| `score()` | Update a scorecard value | `measurable_id`, `score`, `week_offset` |

!!! info "Week Offsets"
    Use `week_offset` to access past or future weeks:
    - Negative values go back in time (e.g., `-1` for last week)
    - Positive values go forward (e.g., `1` for next week)
    - `0` or omitted means current week