# User (`model/users/user.py`)

## Diagram Reference
Maps directly to **`Uzivatel`** in the reference diagram.

## Classes
### `User`
Player profile entity.

#### Attributes
- `username: str`: Unique login identifier.
- `name: str`: Display name.
- `email: str`: Contact email.
- `elo: int`: ELO skill rating (default: `1200`).
- `completed_quests: List[Quest]`: Completed achievements.

#### Methods
- `add_quest(quest: Quest) -> None`: Grants completed quest.
- `get_completed_quests() -> List[Quest]`: Returns completed quests.
- `getEloRating() -> int`: Returns current ELO rating.
