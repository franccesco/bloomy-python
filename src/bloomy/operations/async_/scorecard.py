"""Async scorecard operations for the Bloomy SDK."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from ...models import ScorecardItem, ScorecardWeek
from ...utils.async_base_operations import AsyncBaseOperations

if TYPE_CHECKING:
    import httpx


class AsyncScorecardOperations(AsyncBaseOperations):
    """Async class to handle all operations related to scorecards."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Initialize the async scorecard operations.

        Args:
            client: The async HTTP client to use for API requests.

        """
        super().__init__(client)

    async def current_week(self) -> ScorecardWeek:
        """Retrieve the current week details.

        Returns:
            A ScorecardWeek model instance containing current week details

        """
        response = await self._client.get("weeks/current")
        response.raise_for_status()
        data = response.json()

        return ScorecardWeek(
            id=data["Id"],
            week_number=data["ForWeekNumber"],
            week_start=data["LocalDate"]["Date"],
            week_end=data["ForWeek"],
        )

    async def list(
        self,
        user_id: int | None = None,
        meeting_id: int | None = None,
        show_empty: bool = False,
        week_offset: int | None = None,
    ) -> builtins.list[ScorecardItem]:
        """Retrieve the scorecards for a user or a meeting.

        Args:
            user_id: The ID of the user (defaults to initialized user_id)
            meeting_id: The ID of the meeting
            show_empty: Whether to include scores with None values (default: False)
            week_offset: Offset for the week number to filter scores

        Returns:
            A list of ScorecardItem model instances

        Raises:
            ValueError: If both user_id and meeting_id are provided

        """
        if user_id and meeting_id:
            raise ValueError(
                "Please provide either `user_id` or `meeting_id`, not both."
            )

        if meeting_id:
            response = await self._client.get(f"scorecard/meeting/{meeting_id}")
        else:
            if user_id is None:
                user_id = await self.get_user_id()
            response = await self._client.get(f"scorecard/user/{user_id}")

        response.raise_for_status()
        data = response.json()

        scorecards: list[ScorecardItem] = [
            ScorecardItem(
                id=scorecard["Id"],
                measurable_id=scorecard["MeasurableId"],
                accountable_user_id=scorecard["AccountableUserId"],
                title=scorecard["MeasurableName"],
                target=scorecard["Target"],
                value=scorecard["Measured"],
                week=scorecard["Week"],
                week_id=scorecard["ForWeek"],
                updated_at=scorecard["DateEntered"],
            )
            for scorecard in data["Scores"]
        ]

        # Filter by week offset if provided
        if week_offset is not None:
            week_data = await self.current_week()
            target_week_id = week_data.week_number + week_offset
            scorecards = [s for s in scorecards if s.week_id == target_week_id]

        # Filter out empty values unless show_empty is True
        if not show_empty:
            scorecards = [s for s in scorecards if s.value is not None]

        return scorecards

    async def score(
        self, measurable_id: int, score: float, week_offset: int = 0
    ) -> bool:
        """Update the score for a measurable item for a specific week.

        Args:
            measurable_id: The ID of the measurable item
            score: The score to be assigned to the measurable item
            week_offset: The number of weeks to offset from the current week
                (default: 0)

        Returns:
            True if the score was successfully updated

        """
        week_data = await self.current_week()
        week_id = week_data.week_number + week_offset

        response = await self._client.put(
            f"measurables/{measurable_id}/week/{week_id}",
            json={"value": score},
        )
        response.raise_for_status()
        return response.is_success
