"""A clock a configuration declares: an initial time, an increment, and the countdown.

A clock is a rule about time, so it belongs to the configuration: two games can disagree about how
long a move may take without the engine caring. `games/chess/clocks/fischer.py` and
`games/checkers/clocks/fischer.py` each declare one, and both are in force because they are files in
a `clocks/` directory — `CONFIGURATION_SECTIONS` in `model/game/configuration.py` names this class
as what a module in that section must derive from, and `compose_section` builds one instance of
every `Clock` subclass the section's own files declare.

This is the parent `notes/object_model.md` §13 registered as the intention and §20 recorded as
unbuilt. It exists because a section cannot be composed against a parent class that is not there:
while both shipped clocks derived from nothing, what belonged in `clocks/` was decided by whatever
each file happened to declare rather than by anything a directory could show.

The increment is what makes the clock fair in a game decided on time rather than on the board: a
player who spends a long time on one move is not then punished for every move after it. `add_time`
is separate from `tick` on purpose — the game loop deducts the time a move took and then adds the
increment, and only the second of those is a reward.

Nothing here names a game. An initial time and an increment are what every clock has whatever it is
clocking, which is what `PRD.md` FR-6 requires a clock to declare, and `model/game/clock_fields.py`
describes one for the settings form by asking what it holds.
"""

from typing import Any, Dict, Optional, Union

from model.game.timer import Timer


class Clock:
    """A countdown with a fixed time for each side and an increment added after each move.

    Attributes:
        initial_seconds: Time each side starts with, in seconds.
        increment_seconds: Time added to a player after each move they complete. Zero means
            no increment, which is a clock that simply runs down.
        timer: The countdown holding the running times.
    """

    def __init__(
        self,
        initial_seconds: int = 0,
        increment_seconds: int = 0,
        timer: Optional[Timer] = None,
    ):
        """Initialize a clock.

        Args:
            initial_seconds: Time each side starts with, in seconds. Defaults to 0, which is
                no time at all: a subclass declares its own default, because the time control
                a game is played at is that game's answer and not the engine's.
            increment_seconds: Time added to a player after each move they complete. Defaults
                to 0.
            timer: The timer holding the running times. One is built if not supplied.
        """
        self.initial_seconds = initial_seconds
        self.increment_seconds = increment_seconds
        self.timer: Timer = timer if timer is not None else Timer(initial_seconds)

    @property
    def label(self) -> str:
        """Return the name this clock is saved and shown under.

        A configuration may offer more than one clock, so they are keyed by something stable. The
        class name is that thing: a clock's identity is which kind it is.

        Returns:
            str: The clock's class name.
        """
        return type(self).__name__

    def persisted_values(self) -> Dict[str, Any]:
        """Return the values that may be written to disk.

        Returns:
            Dict[str, Any]: The initial time and the increment.
        """
        return {
            "initial_seconds": self.initial_seconds,
            "increment_seconds": self.increment_seconds,
        }

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
