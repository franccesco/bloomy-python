"""Mixin for shared user operations logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...models import (
    DirectReport,
    Position,
    UserDetails,
    UserListItem,
    UserSearchResult,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class UserOperationsMixin:
    """Shared logic for user operations."""

    def _transform_user_details(
        self,
        data: dict[str, Any],
        direct_reports: list[DirectReport] | None = None,
        positions: list[Position] | None = None,
    ) -> UserDetails:
        """Transform API response to UserDetails model.

        Args:
            data: The raw API response data.
            direct_reports: Optional list of direct reports.
            positions: Optional list of positions.

        Returns:
            A UserDetails model.

        """
        user_details_dict = {
            "id": data["Id"],
            "name": data["Name"],
            "image_url": data["ImageUrl"],
        }

        if direct_reports is not None:
            user_details_dict["direct_reports"] = direct_reports

        if positions is not None:
            user_details_dict["positions"] = positions

        return UserDetails(**user_details_dict)

    def _transform_direct_reports(
        self, data: Sequence[dict[str, Any]]
    ) -> list[DirectReport]:
        """Transform API response to list of DirectReport models.

        Args:
            data: The raw API response data.

        Returns:
            A list of DirectReport models.

        """
        return [
            DirectReport(
                name=report["Name"],
                id=report["Id"],
                image_url=report["ImageUrl"],
            )
            for report in data
        ]

    def _transform_positions(self, data: Sequence[dict[str, Any]]) -> list[Position]:
        """Transform API response to list of Position models.

        Args:
            data: The raw API response data.

        Returns:
            A list of Position models.

        """
        return [
            Position(
                name=position["Group"]["Position"]["Name"],
                id=position["Group"]["Position"]["Id"],
            )
            for position in data
        ]

    def _transform_search_results(
        self, data: Sequence[dict[str, Any]]
    ) -> list[UserSearchResult]:
        """Transform API response to list of UserSearchResult models.

        Args:
            data: The raw API response data.

        Returns:
            A list of UserSearchResult models.

        """
        return [
            UserSearchResult(
                id=user["Id"],
                name=user["Name"],
                description=user["Description"],
                email=user["Email"],
                organization_id=user["OrganizationId"],
                image_url=user["ImageUrl"],
            )
            for user in data
        ]

    def _transform_user_list(
        self, users: Sequence[dict[str, Any]], include_placeholders: bool
    ) -> list[UserListItem]:
        """Transform and filter API response to list of UserListItem models.

        Args:
            users: The raw API response data.
            include_placeholders: Whether to include placeholder users.

        Returns:
            A list of UserListItem models.

        """
        filtered_users = [
            user
            for user in users
            if user["ResultType"] == "User"
            and (include_placeholders or user["ImageUrl"] != "/i/userplaceholder")
        ]

        return [
            UserListItem(
                id=user["Id"],
                name=user["Name"],
                email=user["Email"],
                position=user["Description"],
                image_url=user["ImageUrl"],
            )
            for user in filtered_users
        ]
