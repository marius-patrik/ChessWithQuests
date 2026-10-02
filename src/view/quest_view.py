"""The quest cards.

Each quest in play is shown as a card: what it asks, how far along it is, and what it pays. The
card reads the quest and never changes it, so what a player sees is what the rules believe.
"""

import tkinter as tk
from tkinter import ttk
from typing import List

from model.game.quest import Quest
from model.misc.quest_manager import QuestManager


class QuestCard(ttk.Frame):
    """One quest: its name, its progress, and its reward."""

    def __init__(self, master: tk.Misc, quest: Quest):
        """Build a card for a quest.

        Args:
            master: The widget to build into.
            quest: The `Quest` this card is about.
        """
        super().__init__(master, padding=(8, 4))
        self.quest = quest

        self.title = tk.StringVar()
        self.progress = tk.StringVar()
        self.reward = tk.StringVar()

        heading = ttk.Frame(self)
        heading.pack(fill="x")
        ttk.Label(heading, textvariable=self.title, font=("TkDefaultFont", 11, "bold")).pack(
            side="left"
        )
        ttk.Label(heading, textvariable=self.reward).pack(side="right")

        ttk.Label(self, textvariable=self.progress).pack(anchor="w")
        self.refresh()

    def refresh(self) -> None:
        """Redraw this card from the quest as it now stands.

        Returns:
            None
        """
        current, target = self.quest.progress()
        done = self.quest.validate()
        self.title.set(f"{'✓' if done else '○'} {self.quest.name}")
        self.progress.set(self.quest.description)
        self.reward.set(f"{current}/{target}  ·  {self.quest.reward} pts")


class QuestList(ttk.Frame):
    """Every quest in play, as a column of cards."""

    def __init__(self, master: tk.Misc, quest_manager: QuestManager, limit: int = 6):
        """Build the list.

        Args:
            master: The widget to build into.
            quest_manager: The `QuestManager` whose quests are shown.
            limit: How many cards to show at once, so a long roster does not fill the window.
        """
        super().__init__(master, padding=(8, 4))
        self.quest_manager = quest_manager
        self.limit = limit
        self.cards: List[QuestCard] = []
        self.rebuild()

    def rebuild(self) -> None:
        """Build one card per quest currently in play.

        Returns:
            None
        """
        for card in self.cards:
            card.destroy()
        self.cards = []
        for quest in self.quest_manager.in_play()[: self.limit]:
            card = QuestCard(self, quest)
            card.pack(fill="x", pady=2)
            self.cards.append(card)

    def refresh(self) -> None:
        """Redraw every card, and pick up any quest that has come into play.

        Returns:
            None
        """
        shown = {card.quest for card in self.cards}
        current = self.quest_manager.in_play()
        if len(current[: self.limit]) != len(self.cards) or shown != set(current[: self.limit]):
            self.rebuild()
            return
        for card in self.cards:
            card.refresh()
