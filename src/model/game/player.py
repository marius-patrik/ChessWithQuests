from typing import Optional, Any


class Player:
    def __init__(self, color: int, user: Optional[Any] = None):
        self.color = color
        self.user = user

    def getColor(self) -> int:
        return self.color

    def getUser(self) -> Optional[Any]:
        return self.user

    def setUser(self, user: Any) -> None:
        self.user = user

    def getEloRating(self) -> int:
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


Hrac = Player
