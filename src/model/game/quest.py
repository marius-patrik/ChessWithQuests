"""The quest parent class.

A quest is a parent class with subclasses, exactly as a rule is: the diagram's `Kůň →
Figurka` generalisation applied to a second concept. There is no condition class, because a
condition object would have forced `validate()` to take the thing it validates as an
argument, and the diagram draws `validate() : bool` taking nothing.
"""

from typing import List, Optional, Tuple

from model.game.events import MoveEvent, ResultEvent
from model.game.field import Field

#: A quest that watches the game one move at a time.
WHEN_AFTER_MOVE = "after_move"

#: A quest that judges the game once it has finished.
WHEN_AT_GAME_END = "at_game_end"

#: Every point a quest may watch for.
WHENS = (WHEN_AFTER_MOVE, WHEN_AT_GAME_END)


class Quest:
    """An objective a player can complete during a game.

    Subclasses carry their own logic, the way `Pawn(Piece)` does. The parent holds what
    every quest has — a name, a description, a reward, the moment it watches for, and how
    far along it is — and `validate()` takes no arguments, as the diagram draws it.

    Attributes:
        name: Human-readable quest name.
        description: What the player is being asked to do.
        reward: Experience awarded for completing the quest.
        when: One of `WHENS`; the moment this quest is judged.
        enabled: Whether the quest is in play at all.
        is_completed: True once the quest has been completed, and it stays true.
    """

    #: Name used when the caller supplies none.
    default_name = "Quest"

    #: Description used when the caller supplies none.
    default_description = ""

    #: The moment this quest is judged. Subclasses that judge at a different time override it.
    when = WHEN_AFTER_MOVE

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        reward: int = 10,
        enabled: bool = True,
    ):
        """Create a quest.

        Args:
            name: Human-readable quest name. Defaults to the class's `default_name`.
            description: What the player is being asked to do. Defaults to the class's
                `default_description`.
            reward: Experience awarded for completing the quest.
            enabled: Whether the quest is in play at all.

        Raises:
            ValueError: If `reward` is negative.
        """
        if reward < 0:
            raise ValueError("a quest reward cannot be negative")
        self.name = name or self.default_name
        self.description = self.default_description if description is None else description
        self.reward = reward
        self.enabled = enabled
        self.is_completed = False
        self._current = 0
        self._target = 1

    def parameters(self) -> List[Field]:
        """Declare what the player may configure about this quest.

        Returns:
            List[Field]: One declaration per configurable value. The parent's own `reward`
            and `enabled` are declared by every quest, so a form only has to add the rest.
        """
        return [
            Field("reward", "integer", "Reward", self.reward, minimum=0),
            Field("enabled", "boolean", "Enabled", self.enabled),
        ]

    def progress(self) -> Tuple[int, int]:
        """Report how far along the quest is.

        Returns:
            Tuple[int, int]: The current count and the target, so a card can render `3/5`.
        """
        return self._current, self._target

    def observe_move(self, event: MoveEvent) -> None:
        """Take note of a move that has been played.

        The parent records nothing. A subclass that watches for something overrides this.

        Args:
            event: The move that was played.

        Returns:
            None
        """
        return None

    def observe_result(self, event: ResultEvent) -> None:
        """Take note of a game that has ended.

        The parent records nothing. A subclass that judges the finished game overrides
        this.

        Args:
            event: The finished game.

        Returns:
            None
        """
        return None

    def validate(self) -> bool:
        """Report whether this quest is complete.

        Takes no arguments, exactly as the reference diagram draws `validate() : bool`.
        A quest that has been completed stays completed.

        Returns:
            bool: True once the target has been reached.
        """
        if self.is_completed:
            return True
        if self._current >= self._target:
            self.is_completed = True
        return self.is_completed

    def reset(self) -> None:
        """Clear this quest's progress so it can be played again in a new game.

        Returns:
            None
        """
        self.is_completed = False
        self._current = 0
        self._current = 0

    def _advance(self, amount: int = 1, target: Optional[int] = None) -> None:
        """Record progress towards this quest's target.

        Args:
            amount: How much progress was made.
            target: The quest's target, when this quest has one.

        Returns:
            None
        """
        if target is not None:
            self._target = target
        self._current += amount

    def _complete(self) -> None:
        """Record that this quest's goal has been reached outright.

        Returns:
            None
        """
        self._current = max(self._current, self._target)

    def __repr__(self) -> str:
        """Return a debugging representation naming the quest.

        Returns:
            str: The quest name, when it is judged, and whether it is complete.
        """
        return f"{type(self).__name__}(name={self.name!r}, when={self.when!r}, done={self.is_completed})"
