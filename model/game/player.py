"""Player representation tracking game side, user association, and Elo ratings."""

from typing import Optional, Any


class Player:
    """Represents a chess participant associated with a side and an optional user profile."""

    def __init__(self, color: int, user: Optional[Any] = None):
        """Initialize a Player.

        Args:
            color: Side color (1 for White, -1 for Black).
            user: Optional User profile instance.
        """
        self.color = color
        self.user = user

    def getColor(self) -> int:
        """Get the player's color identifier.

        Returns:
            Color identifier (1 for White, -1 for Black).
        """
        return self.color

    def getUser(self) -> Optional[Any]:
        """Get the associated user profile.

        Returns:
            User profile object or None if not linked.
        """
        return self.user

    def setUser(self, user: Any) -> None:
        """Associate a user profile with this player.

        Args:
            user: User profile instance.
        """
        self.user = user

    def getEloRating(self) -> int:
        """Get the Elo rating of the player from their user profile.

        Returns:
            Integer Elo rating, defaulting to 1200 if unrated.
        """
        if self.user is not None:
            if hasattr(self.user, "elo"):
                return int(self.user.elo)
            if hasattr(self.user, "getEloRating"):
                return int(self.user.getEloRating())
        return 1200

    # Aliases
    get_elo_rating = getEloRating
    get_color = getColor
    get_user = getUser
