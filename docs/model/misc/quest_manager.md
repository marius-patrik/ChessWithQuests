# QuestManager (`model/misc/quest_manager.py`)

## Diagram Reference
Maps directly to **`QuestManager`** in the reference architecture diagram.

## Classes
### `QuestManager`
Registry and validation coordinator for in-game quests.

#### Attributes
- `quests: List[Quest]`: Collection of registered quests.

#### Methods
- `register_quest(quest: Quest) -> None`: Enrolls a quest into the registry.
- `get_quests() -> List[Quest]`: Lists all quests.
- `check_quests(context: Any, user: Optional[User] = None) -> List[Quest]`: Evaluates uncompleted quests and awards them to player.
- `get_completed_quests() -> List[Quest]`: Lists satisfied quests.
