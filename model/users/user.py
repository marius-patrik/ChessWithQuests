"""User profile model encapsulating user identity, ratings, and quest progress."""

from typing import List, Optional, Any


class User:
    """Represents a player user account with rating, identity, and completed achievements."""

    def __init__(
        self,
        username: str,
        name: str = "",
        email: str = "",
        elo: int = 1200,
        completed_quests: Optional[List[Any]] = None,
    ):
        """Initialize a User profile.

        Args:
            username: Unique account handle.
            name: Full name of the user.
            email: User's contact email.
            elo: Current skill rating (default: 1200).
            completed_quests: Optional list of previously completed quests.
        """
        self.username = username
        self.name = name
        self.email = email
        self.elo = elo
        self.completed_quests: List[Any] = completed_quests if completed_quests is not None else []

    def add_quest(self, quest: Any) -> None:
        """Add a completed quest to this user's profile.

        Args:
            quest: Quest instance or identifier.
        """
        if quest not in self.completed_quests:
            self.completed_quests.append(quest)

    def get_completed_quests(self) -> List[Any]:
        """Get the list of quests completed by the user.

        Returns:
            List of completed quests.
        """
        return list(self.completed_quests)

    def getEloRating(self) -> int:
        """Get the user's current Elo rating.

        Returns:
            Current integer Elo rating.
        """
        return self.elo
