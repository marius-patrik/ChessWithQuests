"""Quest manager supervising quest catalog registration, validation, and user rewards."""

from typing import List, Optional, Any

try:
    from model.game.quest import Quest
except ImportError:
    from ..game.quest import Quest


class QuestManager:
    """Registry maintaining active game quests, trigger checks, and user completions."""

    def __init__(self, quests: Optional[List[Quest]] = None):
        """Initialize a QuestManager instance.

        Args:
            quests: Optional initial list of Quest objects.
        """
        self.quests: List[Quest] = quests if quests is not None else []

    def register_quest(self, quest: Quest) -> None:
        """Register a new quest in the active pool.

        Args:
            quest: Quest instance to register.
        """
        if quest not in self.quests:
            self.quests.append(quest)

    def get_quests(self) -> List[Quest]:
        """Retrieve all registered quests.

        Returns:
            List copy of all registered Quest instances.
        """
        return list(self.quests)

    def check_quests(self, context: Any, user: Optional[Any] = None) -> List[Quest]:
        """Evaluate all uncompleted quests against game context and award them to user.

        Args:
            context: Context data (e.g. GameManager state) passed to quest validators.
            user: Optional User profile to credit with newly completed quests.

        Returns:
            List of quests newly completed during this check.
        """
        completed_now: List[Quest] = []
        for q in self.quests:
            if not q.is_completed and q.validate(context):
                completed_now.append(q)
                if user is not None and hasattr(user, "add_quest"):
                    user.add_quest(q)
        return completed_now

    def get_completed_quests(self) -> List[Quest]:
        """Retrieve all currently completed quests.

        Returns:
            List of quests with is_completed set to True.
        """
        return [q for q in self.quests if q.is_completed]
