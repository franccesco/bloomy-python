"""User operations for the Bloomy SDK."""

from __future__ import annotations

from ..models import DirectReport, Position, UserDetails, UserListItem, UserSearchResult
from ..utils.base_operations import BaseOperations
from .mixins.users import UserOperationsMixin


class UserOperations(BaseOperations, UserOperationsMixin):
    """Class to handle all operations related to users."""

    def details(
        self,
        user_id: int | None = None,
        direct_reports: bool = False,
        positions: bool = False,
        all: bool = False,
    ) -> UserDetails:
        """Retrieve details of a specific user.

        Args:
            user_id: The ID of the user (default: the current user ID)
            direct_reports: Whether to include direct reports (default: False)
            positions: Whether to include positions (default: False)
            all: Whether to include both direct reports and positions (default: False)

        Returns:
            A UserDetails model containing user details

        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(f"users/{user_id}")
        response.raise_for_status()
        data = response.json()

        direct_reports_data = None
        positions_data = None

        if direct_reports or all:
            direct_reports_data = self.direct_reports(user_id)

        if positions or all:
            positions_data = self.positions(user_id)

        return self._transform_user_details(data, direct_reports_data, positions_data)

    def direct_reports(self, user_id: int | None = None) -> list[DirectReport]:
        """Retrieve direct reports of a specific user.

        Args:
            user_id: The ID of the user (default: the current user ID)

        Returns:
            A list of DirectReport models containing direct report details

        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(f"users/{user_id}/directreports")
        response.raise_for_status()
        data = response.json()

        return self._transform_direct_reports(data)

    def positions(self, user_id: int | None = None) -> list[Position]:
        """Retrieve positions of a specific user.

        Args:
            user_id: The ID of the user (default: the current user ID)

        Returns:
            A list of Position models containing position details

        """
        if user_id is None:
            user_id = self.user_id

        response = self._client.get(f"users/{user_id}/seats")
        response.raise_for_status()
        data = response.json()

        return self._transform_positions(data)

    def search(self, term: str) -> list[UserSearchResult]:
        """Search for users based on a search term.

        Args:
            term: The search term

        Returns:
            A list of UserSearchResult models containing search results

        """
        response = self._client.get("search/user", params={"term": term})
        response.raise_for_status()
        data = response.json()

        return self._transform_search_results(data)

    def all(self, include_placeholders: bool = False) -> list[UserListItem]:
        """Retrieve all users in the system.

        Args:
            include_placeholders: Whether to include placeholder users (default: False)

        Returns:
            A list of UserListItem models containing user details

        """
        response = self._client.get("search/all", params={"term": "%"})
        response.raise_for_status()
        users = response.json()

        return self._transform_user_list(users, include_placeholders)
