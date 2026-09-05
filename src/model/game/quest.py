"""Quest module defining achievement objectives, condition evaluation, and completion state."""

from typing import Optional, Callable, Any


class Quest:
    """Represents a gameplay quest or achievement objective with rewards."""

    def __init__(
        self,
        name: str,
        description: str = "",
        condition_fn: Optional[Callable[[Any], bool]] = None,
        reward_points: int = 10,
    ):
        """Initialize a Quest instance.

        Args:
            name: Title of the quest.
            description: Detailed goal description.
            condition_fn: Callable evaluating whether the quest is met in a context.
            reward_points: Score or experience points awarded upon completion.
        """
        self.name = name
        self.description = description
        self.condition_fn = condition_fn
        self.reward_points = reward_points
        self.is_completed = False

    def validate(self, context: Optional[Any] = None) -> bool:
        """Evaluate quest conditions against provided game context.

        Args:
            context: Context passed to condition_fn (e.g. GameManager state).

        Returns:
            True if quest is satisfied or was already completed, False otherwise.
        """
        if self.is_completed:
            return True
        if self.condition_fn is not None:
            result = bool(self.condition_fn(context))
            if result:
                self.is_completed = True
            return result
        return self.is_completed

    def complete(self) -> None:
        """Mark this quest as explicitly completed."""
        self.is_completed = True
