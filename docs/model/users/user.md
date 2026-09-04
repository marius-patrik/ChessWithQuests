# User (`model/users/user.py`)

## Diagram Reference
Maps directly to **`Uzivatel`** in the reference diagram.

## Classes
### `User` (Alias: `Uzivatel`)
Player profile entity.

#### Attributes
- `username: str` (`uzivatelske_jmeno`): Unique login identifier.
- `name: str` (`jmeno`): Display name.
- `email: str`: Contact email.
- `elo: int`: ELO skill rating (default: `1200`).
- `completed_quests: List[Quest]` (`splnene_kwesty`): Completed achievements.

#### Methods
- `add_quest(quest: Quest) -> None` (`pridej_quest`): Grants completed quest.
- `get_completed_quests() -> List[Quest]`: Returns completed quests.
- `getEloRating() -> int`: Returns current ELO rating.
