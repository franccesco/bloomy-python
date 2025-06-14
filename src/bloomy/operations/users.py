"""User operations for the Bloomy SDK."""

from __future__ import annotations

from ..models import DirectReport, Position, UserDetails, UserListItem, UserSearchResult
from ..utils.base_operations import BaseOperations


class UserOperations(BaseOperations):
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

        user_details_dict = {
            "id": data["Id"],
            "name": data["Name"],
            "image_url": data["ImageUrl"],
        }

        if direct_reports or all:
            user_details_dict["direct_reports"] = self.direct_reports(user_id)

        if positions or all:
            user_details_dict["positions"] = self.positions(user_id)

        return UserDetails(**user_details_dict)

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

        return [
            DirectReport(
                name=report["Name"],
                id=report["Id"],
                image_url=report["ImageUrl"],
            )
            for report in data
        ]

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

        return [
            Position(
                name=position["Group"]["Position"]["Name"],
                id=position["Group"]["Position"]["Id"],
            )
            for position in data
        ]

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
