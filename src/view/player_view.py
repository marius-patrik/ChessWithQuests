"""One player's panel.

A panel shows the three things about a player that the board does not: who they are, how long
they have, and what they have taken and lost. It reads the player and the board; it never
changes them.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from model.game.board import Board
from model.game.manager import GameManager
from model.game.player import Player


def format_seconds(seconds: int) -> str:
    """Return a clock's remaining time as a player reads it.

    Args:
        seconds: The seconds remaining.

    Returns:
        str: `mm:ss`, or `-mm:ss` once the clock has run out, because a negative clock is a
        loss rather than a countdown to it.
    """
    sign = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    return f"{sign}{seconds // 60:02d}:{seconds % 60:02d}"


class PlayerView(ttk.Frame):
    """The panel for one side: name, clock, and the pieces taken and lost."""

    def __init__(
        self,
        master: tk.Misc,
        player: Player,
        manager: Optional[GameManager] = None,
        side: str = "bottom",
    ):
        """Build a panel for a player.

        Args:
            master: The widget to build into.
            player: The `Player` this panel is about.
            manager: The `GameManager` holding this player's clock.
            side: Which edge of the board this panel sits on, `top` or `bottom`. It decides
                nothing about the game; it only decides the order things are stacked in.
        """
        super().__init__(master, padding=(10, 6))
        self.player = player
        self.manager = manager
        self.side = side

        self.name = tk.StringVar(value=self._display_name())
        self.clock = tk.StringVar(value=format_seconds(0))
        self.captured = tk.StringVar(value="")
        self.lost = tk.StringVar(value="")

        ttk.Label(self, textvariable=self.name, font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        ttk.Label(self, textvariable=self.clock, font=("TkDefaultFont", 16)).pack(anchor="w")

        taken = ttk.Label(self, textvariable=self.captured)
        taken.pack(anchor="w")
        gone = ttk.Label(self, textvariable=self.lost)
        gone.pack(anchor="w")

    def _display_name(self) -> str:
        """Return the name to show for this player.

        Returns:
            str: The user's name when there is one, else the side's colour.
        """
        user = self.player.getUser()
        if user is not None and getattr(user, "name", ""):
            return str(user.name)
        return "White" if self.player.getColor() == 1 else "Black"

    def refresh(self, board: Optional[Board] = None, active_color: int = 1) -> None:
        """Redraw this panel from the game as it now stands.

        Args:
            board: The board to read captures from. None reads the board the manager holds.
            active_color: The colour whose turn it is.

        Returns:
            None
        """
        self.name.set(self._display_name())
        self.clock.set(format_seconds(self._remaining()))
        self.captured.set(self._captured_text(board))
        self.lost.set(self._lost_text(board))

    def _remaining(self) -> int:
        """Return this player's remaining time.

        Returns:
            int: The seconds left on this player's clock, or zero before a game is running.
        """
        if self.manager is None:
            return 0
        return self.manager.timer.get_time(self.player.getColor())

    def _taken(self, board: Board) -> str:
        """Return the glyphs of the pieces this player has taken.

        Args:
            board: The board to read captures from.

        Returns:
            str: The glyphs, in the order they were taken.
        """
        colour = self.player.getColor()
        captured = board.captured_black if colour == 1 else board.captured_white
        return " ".join(piece.getSymbol() or "?" for piece in captured)

    def _captured_text(self, board: Board) -> str:
        """Return the label for the pieces this player has taken.

        Args:
            board: The board to read captures from.

        Returns:
            str: The label and its glyphs, or just the label when nothing has been taken.
        """
        taken = self._taken(board)
        return f"Taken: {taken}" if taken else "Taken:"

    def _lost_text(self, board: Board) -> str:
        """Return the label for the pieces this player has lost.

        Args:
            board: The board to read the opponent's captures from.

        Returns:
            str: The label and its glyphs, or just the label when nothing has been lost.
        """
        colour = self.player.getColor()
        captured = board.captured_white if colour == 1 else board.captured_black
        lost = " ".join(piece.getSymbol() or "?" for piece in captured)
        return f"Lost: {lost}" if lost else "Lost:"
