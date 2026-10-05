"""Player representation tracking game side, user association, and Elo ratings."""

from typing import Optional, Any


class Player:
    """Represents a participant associated with a side and an optional user profile."""

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
            rating = getattr(self.user, "elo", None)
            if rating is not None:
                return int(rating)
            get_rating = getattr(self.user, "getEloRating", None)
            if callable(get_rating):
                return int(get_rating())
        return 1200


#: Czech alias for `Player`, as `PRD.md` section 5 and `Hrac` in the diagram require.
Hrac = Player
