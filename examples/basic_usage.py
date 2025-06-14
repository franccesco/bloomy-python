#!/usr/bin/env python3
"""Basic usage example for the Bloomy Python SDK."""

from bloomy import Client
from bloomy.exceptions import AuthenticationError, BloomyError


def main():
    """Demonstrate basic usage of the Bloomy SDK."""
    # Initialize client (will use BG_API_KEY environment variable if set)
    try:
        client = Client()
    except ValueError:
        print("No API key found. Please set BG_API_KEY environment variable.")
        print("Or configure with username/password:")
        print()
        print("from bloomy import Configuration")
        print("config = Configuration()")
        print('config.configure_api_key("username", "password", store_key=True)')
        return

    try:
        # Get current user information
        print("Current User:")
        user = client.user.details()
        print(f"  Name: {user['name']}")
        print(f"  ID: {user['id']}")
        print()

        # List meetings
        print("Meetings:")
        meetings = client.meeting.list()
        for meeting in meetings[:5]:  # Show first 5
            print(f"  - {meeting['title']} (ID: {meeting['id']})")
        print()

        # List todos
        print("Todos:")
        todos = client.todo.list()
        for todo in todos[:5]:  # Show first 5
            status = "✓" if todo["status"] == "Complete" else "○"
            print(f"  {status} {todo['title']} (Due: {todo['due_date']})")
        print()

        # List current goals
        print("Goals (Rocks):")
        goals = client.goal.list()
        if isinstance(goals, list):
            for goal in goals[:5]:  # Show first 5
                print(f"  - {goal['title']} ({goal['status']})")
        print()

        # Get current week scorecard
        print("Current Week:")
        week = client.scorecard.current_week()
        print(f"  Week #{week['week_number']}")
        print(f"  {week['week_start']} to {week['week_end']}")

    except AuthenticationError:
        print("Authentication failed. Please check your API key.")
    except BloomyError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
