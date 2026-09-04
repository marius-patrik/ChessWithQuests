from typing import List, Optional, Any


class User:
    def __init__(
        self,
        username: str,
        name: str = "",
        email: str = "",
        elo: int = 1200,
        completed_quests: Optional[List[Any]] = None,
    ):
        self.username = username
        self.name = name
        self.email = email
        self.elo = elo
        self.completed_quests: List[Any] = completed_quests if completed_quests is not None else []

    def add_quest(self, quest: Any) -> None:
        if quest not in self.completed_quests:
            self.completed_quests.append(quest)

    def get_completed_quests(self) -> List[Any]:
        return list(self.completed_quests)

    def getEloRating(self) -> int:
        return self.elo
