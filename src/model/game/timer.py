"""Chess clock and countdown timer tracking elapsed and remaining time for each player."""

from typing import List, Union


class Timer:
    """Manages player turn clocks, increments, countdown ticks, and expiration."""

    def __init__(self, initial_time: int = 600):
        """Initialize game timers.

        Args:
            initial_time: Initial time per player in seconds (default: 600).
        """
        self.initial_time = initial_time
        self.player_times: List[int] = [initial_time, initial_time]

    def _get_player_index(self, player: Union[int, str]) -> int:
        """Resolve player identifier to clock array index.

        Args:
            player: 1/"white" for index 0, -1/"black" for index 1, or 0/1 integer index.

        Returns:
            0 or 1 index.
        """
        if player == 1 or player == "white":
            return 0
        elif player == -1 or player == "black":
            return 1
        elif player in (0, 1):
            return player
        return 0

    def reset_time(self) -> None:
        """Reset both player clocks to the initial time."""
        self.player_times = [self.initial_time, self.initial_time]

    def tick(self, player: int, elapsed_seconds: int = 1) -> None:
        """Deduct elapsed seconds from a player's clock.

        Args:
            player: Player identifier (1 for White, -1 for Black, or index).
            elapsed_seconds: Number of seconds to deduct (default: 1).
        """
        idx = self._get_player_index(player)
        self.player_times[idx] = max(0, self.player_times[idx] - elapsed_seconds)

    countdown = tick

    def add_time(self, player: int, increment_seconds: int) -> None:
        """Add increment time to a player's clock.

        Args:
            player: Player identifier (1 for White, -1 for Black, or index).
            increment_seconds: Seconds to add to player's clock.
        """
        idx = self._get_player_index(player)
        self.player_times[idx] += increment_seconds

    def get_time(self, player: int) -> int:
        """Get remaining time in seconds for a player.

        Args:
            player: Player identifier (1 for White, -1 for Black, or index).

        Returns:
            Remaining seconds.
        """
        idx = self._get_player_index(player)
        return self.player_times[idx]

    def is_expired(self, player: int) -> bool:
        """Check if a player's clock has run out of time.

        Args:
            player: Player identifier (1 for White, -1 for Black, or index).

        Returns:
            True if remaining time is 0 or less, False otherwise.
        """
        return self.get_time(player) <= 0
