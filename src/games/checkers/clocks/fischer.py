"""The checkers clocks.

A clock is a rule about time, so it belongs to the configuration: two games can disagree about how
long a move may take without the engine caring. This is the same Fischer clock the chess
configuration ships, at the time control English draughts is normally played with — twelve minutes a
side and three seconds added after every move — and it is a separate file rather than an import
because a configuration is meant to be copyable on its own: `cp -r games/checkers games/house` has
to produce a directory that works, and a variant whose clock came from another game would not be
one.
"""

from typing import Optional

from model.game.clock import Clock
from model.game.timer import Timer

#: The usual time control for a game of English draughts: twelve minutes a side.
INITIAL_SECONDS: int = 720

#: The seconds added to a player's clock after every move they complete.
INCREMENT_SECONDS: int = 3


class Fischer(Clock):
    """The clock a game of English draughts is normally played under.

    Twelve minutes a side with a three-second increment, which is the time control the game's own
    rulebook literature uses and is a declaration of draughts rather than an engine default: the
    chess configuration plays ten minutes with five.
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
