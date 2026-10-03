"""The checkers clocks.

A clock is a rule about time, so it belongs to the configuration: two games can disagree
about how long a move may take without the engine caring. This is the same Fischer clock the
chess configuration ships, at the time control English draughts is normally played with —
twelve minutes a side and three seconds added after every move — and it is a separate file
rather than an import because a configuration is meant to be copyable on its own: `cp -r
games/checkers games/house` has to produce a directory that works, and a variant whose clock
came from another game would not be one.
"""

from typing import Optional, Union

from model.game.timer import Timer

#: The usual time control for a game of English draughts: twelve minutes a side.
INITIAL_SECONDS: int = 720

#: The seconds added to a player's clock after every move they complete.
INCREMENT_SECONDS: int = 3


class Fischer:
    """A clock that adds a fixed increment to a player after each of their moves.

    The increment is what makes the clock fair in a game decided on time rather than on the
    board: a player who spends a long time on one move is not then punished for every move
    after it. `add_time` is separate from `tick` on purpose — the game loop deducts the time
    a move took and then adds the increment, and only the second of those is a reward.
    """

    def __init__(
        self,
        initial_seconds: int = INITIAL_SECONDS,
        increment_seconds: int = INCREMENT_SECONDS,
        timer: Optional[Timer] = None,
    ):
        """Initialize a Fischer clock.

        Args:
            initial_seconds: Time each side starts with, in seconds.
            increment_seconds: Time added to a player after each move they complete.
            timer: The timer holding the running times. One is built if not supplied.
        """
        self.initial_seconds = initial_seconds
        self.increment_seconds = increment_seconds
        self.timer: Timer = timer or Timer(initial_seconds)

    def reset(self) -> None:
        """Return both clocks to their starting time.

        Returns:
            None
        """
        self.timer.reset_time()

    def tick(self, player: Union[int, str], elapsed_seconds: int = 1) -> None:
        """Charge a player for the time a move took.

        Args:
            player: The player whose clock runs, as a colour or an index.
            elapsed_seconds: Seconds to deduct.

        Returns:
            None
        """
        self.timer.tick(player, elapsed_seconds)

    def credit(self, player: Union[int, str]) -> None:
        """Add the increment to a player who has just completed a move.

        Args:
            player: The player who moved, as a colour or an index.

        Returns:
            None
        """
        if self.increment_seconds:
            self.timer.add_time(player, self.increment_seconds)

    def get_time(self, player: Union[int, str]) -> int:
        """Return how long a player has left.

        Args:
            player: The player to read, as a colour or an index.

        Returns:
            int: The seconds remaining, never below zero.
        """
        return self.timer.get_time(player)

    def is_expired(self, player: Union[int, str]) -> bool:
        """Report whether a player has run out of time.

        Args:
            player: The player to read, as a colour or an index.

        Returns:
            bool: True when that player has no time left.
        """
        return self.timer.is_expired(player)

    def __repr__(self) -> str:
        """Return a readable description of this clock.

        Returns:
            str: The clock's starting time and increment.
        """
        return (
            f"{type(self).__name__}(initial_seconds={self.initial_seconds}, "
            f"increment_seconds={self.increment_seconds})"
        )
