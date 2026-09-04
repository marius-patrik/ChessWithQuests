from typing import List, Optional, Any

try:
    from model.game.quest import Quest
except ImportError:
    from ..game.quest import Quest


class QuestManager:
    def __init__(self, quests: Optional[List[Quest]] = None):
        self.quests: List[Quest] = quests if quests is not None else []

    def register_quest(self, quest: Quest) -> None:
        if quest not in self.quests:
            self.quests.append(quest)

    def get_quests(self) -> List[Quest]:
        return list(self.quests)

    def check_quests(self, context: Any, user: Optional[Any] = None) -> List[Quest]:
        completed_now: List[Quest] = []
        for q in self.quests:
            if not q.is_completed and q.validate(context):
                completed_now.append(q)
                if user is not None and hasattr(user, "add_quest"):
                    user.add_quest(q)
        return completed_now

    def get_completed_quests(self) -> List[Quest]:
        return [q for q in self.quests if q.is_completed]
