# Quest (`model/game/quest.py`)

## Diagram Reference
Maps directly to **`Quest`** in the reference architecture diagram.

## Classes
### `Quest`
Represents an in-game quest or achievement with evaluation conditions.

#### Attributes
- `name: str` (`nazev`): Quest name.
- `description: str` (`popis`): Quest objective description.
- `condition_fn: Optional[Callable[[Any], bool]]`: Predicate function evaluating fulfillment.
- `reward_points: int`: Points granted upon completion.
- `is_completed: bool`: Completion state flag.

#### Methods
- `validate(context: Optional[Any] = None) -> bool`: Tests condition predicate against game context.
- `complete() -> None`: Manually marks quest as fulfilled.
