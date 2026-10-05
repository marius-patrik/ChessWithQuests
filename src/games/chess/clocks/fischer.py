"""The chess clocks.

A clock is a rule about time, so it belongs to the configuration: two games can disagree about how
long a move may take without the engine caring. `Fischer` is the orthodox default — a fixed time for
each side, plus an increment added after every move the player completes — and it is a file in this
directory because `clocks/` is composed out of the files it holds.

A separate file rather than a shared import, because a configuration is meant to be copyable on its
own: `cp -r games/chess games/house` has to produce a directory that works, and a variant whose
clock came from another game would not be one.
"""

from typing import Optional

from model.game.clock import Clock
from model.game.timer import Timer

#: The orthodox default: ten minutes a side.
INITIAL_SECONDS: int = 600

#: The orthodox default increment, in seconds, added after each move.
INCREMENT_SECONDS: int = 5


class Fischer(Clock):
    """A clock that adds a fixed increment to a player after each of their moves.

    The increment is what makes the clock fair in a game decided on time rather than on the board: a
    player who spends a long time on one move is not then punished for every move after it. Only the
    defaults are declared here; `add_time` on the parent is separate from `tick` on purpose, because
    the game loop deducts the time a move took and then adds the increment, and only the second of
    those is a reward.
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
        super().__init__(
            initial_seconds=initial_seconds,
            increment_seconds=increment_seconds,
            timer=timer,
        )
