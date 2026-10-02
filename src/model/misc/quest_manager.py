"""Holding the quests in play for one game.

Scope is split deliberately, and the split is the requirement: quests **in play for the
current game** live here, and quests a **user** has completed live on the user. Nothing in
this class is a permanent record, so a game that ends takes its quests with it and the next
game starts from the quests its configuration declares.
"""

from typing import Iterable, List, Optional

from model.game.events import MoveEvent, ResultEvent
from model.game.quest import WHEN_AFTER_MOVE, WHEN_AT_GAME_END, Quest


class QuestManager:
    """The quests in play for one game, and what they have made of it."""

    def __init__(self, quests: Optional[Iterable[Quest]] = None):
        """Start a game with a set of quests.

        Args:
            quests: The quests in play. A new list is taken, so the caller's list is not
                mutated.
        """
        self.quests: List[Quest] = list(quests) if quests is not None else []

    def register_quest(self, quest: Quest) -> None:
        """Put a quest into play.

        Args:
            quest: The quest to add.

        Returns:
            None
        """
        if quest not in self.quests:
            self.quests.append(quest)

    def get_quests(self) -> List[Quest]:
        """Return the quests in play.

        Returns:
            List[Quest]: A copy of the in-play list.
        """
        return list(self.quests)

    def in_play(self, when: Optional[str] = None) -> List[Quest]:
        """Return the quests in play, optionally narrowed to one moment.

        Args:
            when: One of `WHEN_AFTER_MOVE` or `WHEN_AT_GAME_END`, or None for all of them.

        Returns:
            List[Quest]: The quests matching the requested moment.
        """
        if when is None:
            return self.get_quests()
        return [quest for quest in self.quests if quest.when == when]

    def observe_move(self, event: MoveEvent) -> List[Quest]:
        """Tell every `after_move` quest about a move and collect what it completed.

        Args:
            event: The move that was played.

        Returns:
            List[Quest]: The quests that became complete on this move.
        """
        return self._observe(WHEN_AFTER_MOVE, event)

    def observe_result(self, event: ResultEvent) -> List[Quest]:
        """Tell every `at_game_end` quest about the finished game and collect what completed.

        Args:
            event: The finished game.

        Returns:
            List[Quest]: The quests that became complete when the game ended.
        """
        return self._observe(WHEN_AT_GAME_END, event)

    def _observe(self, when: str, event: object) -> List[Quest]:
        """Deliver an event to the quests waiting for it and collect the completions.

        Args:
            when: The moment the quests being told about this event watch for.
            event: The move or the finished game.

        Returns:
            List[Quest]: The quests that were not already complete and now are.
        """
        completed: List[Quest] = []
        for quest in self.in_play(when):
            if quest.is_completed or not quest.enabled:
                continue
            if when == WHEN_AFTER_MOVE:
                quest.observe_move(event)  # type: ignore[arg-type]
            else:
                quest.observe_result(event)  # type: ignore[arg-type]
            if quest.validate():
                completed.append(quest)
        return completed

    def get_completed_quests(self) -> List[Quest]:
        """Return the quests completed during this game.

        Returns:
            List[Quest]: The quests whose `validate()` has returned True.
        """
        return [quest for quest in self.quests if quest.validate()]

    def total_reward(self) -> int:
        """Return the experience this game's completed quests are worth.

        Experience is derived from the completed quests rather than stored, so a user gains
        no field for it and cannot hold a total that disagrees with its quests.

        Returns:
            int: The sum of the rewards of every completed quest.
        """
        return sum(quest.reward for quest in self.quests if quest.validate())

    def reset(self) -> None:
        """Clear every quest's progress so the same set can be played again.

        Returns:
            None
        """
        for quest in self.quests:
            quest.reset()
