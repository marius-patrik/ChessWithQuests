from typing import Optional, Callable, Any


class Quest:
    def __init__(
        self,
        name: str,
        description: str = "",
        condition_fn: Optional[Callable[[Any], bool]] = None,
        reward_points: int = 10,
    ):
        self.name = name
        self.description = description
        self.condition_fn = condition_fn
        self.reward_points = reward_points
        self.is_completed = False

    def validate(self, context: Optional[Any] = None) -> bool:
        if self.is_completed:
            return True
        if self.condition_fn is not None:
            result = bool(self.condition_fn(context))
            if result:
                self.is_completed = True
            return result
        return self.is_completed

    def complete(self) -> None:
        self.is_completed = True

    # Czech aliases from diagram
    nazev = property(lambda self: self.name)
    popis = property(lambda self: self.description)
