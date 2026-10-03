"""The whole game, on screen.

`PlayerGameView` is the window's arrangement: both player panels, the board, the turn
indicator, the move history, the quest cards and the status footer. It owns the refresh and
nothing else — every click goes to the controller and every redraw reads the model.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

from controller.window_controller import WindowController
from model.game.manager import GameManager
from model.misc.notation import pos_to_algebraic
from view.game_view import BoardView
from view.player_view import PlayerView
from view.quest_view import QuestList

#: How often the window redraws itself, in milliseconds. Clocks and quests both change without
#: a click, so the view cannot wait for one.
REFRESH_INTERVAL_MS = 500

#: The states in which the game is over and no further move may be played.
TERMINAL_STATES = (
    GameManager.STATE_TIMEOUT,
    GameManager.STATE_CHECKMATE,
    GameManager.STATE_STALEMATE,
)

#: The state a game can be in, and what the footer says about it.
STATE_LABELS = {
    GameManager.STATE_TIMEOUT: "Time is up.",
    GameManager.STATE_CHECKMATE: "Checkmate.",
    GameManager.STATE_STALEMATE: "Stalemate — the game is drawn.",
    GameManager.STATE_CHECK: "Check.",
    GameManager.STATE_IN_PROGRESS: "",
}


class PlayerGameView(ttk.Frame):
    """The playing window: panels, board, history, quests and a status footer."""

    def __init__(
        self,
        master: tk.Misc,
        window_controller: WindowController,
        square_size: int = 56,
        on_settings=None,
        on_new_game_request=None,
    ):
        """Build the window.

        Args:
            master: The widget to build into.
            window_controller: The controller every click and every refresh goes through.
            square_size: The width and height of one board square, in pixels.
        """
        super().__init__(master, padding=10)
        self.window_controller = window_controller
        self.on_settings = on_settings
        self.on_new_game_request = on_new_game_request
        self.manager: GameManager = window_controller.game_controller.game_manager

        self.turn = tk.StringVar()
        self.status = tk.StringVar(value="Welcome to ChessWithQuests")

        self._build_layout(square_size)
        self.refresh()

    def _build_layout(self, square_size: int) -> None:
        """Place every widget.

        Args:
            square_size: The width and height of one board square, in pixels.

        Returns:
            None
        """
        heading = ttk.Frame(self)
        heading.pack(fill="x")
        ttk.Label(heading, text="ChessWithQuests", font=("TkDefaultFont", 16, "bold")).pack(
            side="left"
        )
        ttk.Button(heading, text="New game", command=self.on_new_game).pack(side="right")
        if self.on_settings is not None:
            ttk.Button(heading, text="Settings", command=self.on_settings).pack(
                side="right", padx=(0, 6)
            )
        ttk.Button(heading, text="Quit", command=self._quit).pack(side="right", padx=(0, 6))

        top = self.manager.players[-1] if self.manager.players else None
        bottom = self.manager.players[0] if self.manager.players else None

        self.top_player = PlayerView(self, top, self.manager, side="top") if top else None
        if self.top_player is not None:
            self.top_player.pack(fill="x")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, textvariable=self.turn, font=("TkDefaultFont", 12)).pack(anchor="w")
        self.board_view = BoardView(
            left,
            self.manager.board,
            on_square_clicked=self.on_square_clicked,
            square_size=square_size,
        )
        self.board_view.pack(pady=6)
        self.bottom_player = (
            PlayerView(left, bottom, self.manager, side="bottom") if bottom else None
        )
        if self.bottom_player is not None:
            # Packed into `left`, beside the board. Packed into `self` it came after `body`,
            # which takes all the slack, so on a short window the panel and the footer were
            # squeezed to nothing and silently stopped appearing.
            self.bottom_player.pack(fill="x")

        right = ttk.Frame(body, padding=(12, 0))
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(right, text="Quests", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        self.quest_list = QuestList(right, self.manager.quest_manager)
        self.quest_list.pack(fill="both", expand=True)

        ttk.Label(right, text="Moves", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
        self.history = tk.Listbox(right, height=10, width=28)
        self.history.pack(fill="both", expand=True)

        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w").pack(
            fill="x", pady=(8, 0)
        )

    def on_square_clicked(self, position: Tuple[int, int]) -> None:
        """Hand a clicked square to the controller and redraw.

        Args:
            position: The (row, col) the player clicked.

        Returns:
            None
        """
        # Only a finished game refuses clicks. Check is an ordinary position the player has to
        # answer, so treating it as terminal froze the board for the rest of the game the
        # moment anybody was put in check.
        if self.manager.get_state() in TERMINAL_STATES:
            self.refresh()
            return

        result = self.window_controller.on_square_clicked(position)
        action = result.get("action")

        if action in ("selected", "reselected"):
            controller = self.window_controller.game_controller
            self.board_view.set_selection(controller.selected_square, result.get("valid_moves", []))
        else:
            self.board_view.set_selection(None, [])

        if action == "moved":
            self.status.set("Move played.")
            if self.manager.get_state() != GameManager.STATE_IN_PROGRESS:
                self.manager.finish_game()
        elif action == "invalid":
            self.status.set("That is not a legal move.")

        self.refresh()

    def reload(self, manager: GameManager) -> None:
        """Point this view at a different game and redraw it.

        Args:
            manager: The `GameManager` of the game to show from now on.

        Returns:
            None
        """
        self.manager = manager
        # The panels hold the manager and the quest manager they were built with, so swapping
        # the game without rebinding them left the clocks and quests showing the old game.
        for panel in (self.top_player, self.bottom_player):
            if panel is not None:
                panel.manager = manager
        self.quest_list.quest_manager = manager.quest_manager
        self.board_view.refresh(manager.board)
        self.board_view.set_selection(None, [])
        self.quest_list.rebuild()
        self.history.delete(0, "end")
        self.refresh()

    def on_new_game(self) -> None:
        """Offer the game chooser again, then deal a new game of what was chosen.

        Choosing the configuration is the player's decision and it belongs in front of every
        game, not only the first one, so New game opens the same modal the program did.

        Returns:
            None
        """
        if self.on_new_game_request is not None:
            self.on_new_game_request()
            return
        self.manager.new_game()
        self.window_controller.game_controller.reset_selection()
        self.window_controller.set_status("New game.")
        self.board_view.set_selection(None, [])
        self.board_view.refresh(self.manager.board)
        self.quest_list.rebuild()
        self.refresh()

    def refresh(self) -> None:
        """Redraw every widget from the game as it now stands.

        Returns:
            None
        """
        board = self.manager.board
        active = self.manager.active_player
        state = self.manager.get_state()

        self.board_view.refresh(board)
        self.board_view.set_in_check(
            self.manager.move_validator.find_royal(active, board)
            if state == GameManager.STATE_CHECK
            else None
        )

        if state in TERMINAL_STATES:
            self.turn.set("Game over")
        else:
            self.turn.set("White to move" if active == 1 else "Black to move")

        for panel in (self.top_player, self.bottom_player):
            if panel is not None:
                panel.refresh(board, active)
        self.quest_list.refresh()

        if state not in TERMINAL_STATES:
            # B5: the footer was only ever set, never cleared, so it kept announcing the
            # previous game's result.
            self.status.set(self.window_controller.status_message)
        label = STATE_LABELS.get(state, "")
        if label and state in TERMINAL_STATES:
            result = self.manager.result
            if result is not None:
                winner = result.winner
                if winner == 1:
                    label = f"Checkmate — White wins ({result.reason})."
                elif winner == -1:
                    label = f"Checkmate — Black wins ({result.reason})."
                else:
                    label = f"Draw ({result.reason})."
            self.status.set(label)

        self._refresh_history()

    def _refresh_history(self) -> None:
        """Redraw the move list from the game's recorded moves.

        Returns:
            None
        """
        moves = self.manager.game_logger.get_moves()
        if self.history.size() == len(moves):
            return
        self.history.delete(0, "end")
        for number, move in enumerate(moves, start=1):
            # Notated rather than printed as coordinates: the notation helper is what the
            # transcript uses, so the list and the export cannot disagree.
            start = pos_to_algebraic(move.start_pos)
            end = pos_to_algebraic(move.end_pos)
            self.history.insert("end", f"{number}. {start} – {end}")

    def _quit(self) -> None:
        """Close the window.

        Returns:
            None
        """
        self.window_controller.stop()
        # The master is the shell frame, not the window: destroying it left the process alive
        # with a blank window and a running mainloop.
        self.winfo_toplevel().destroy()

    def start_auto_refresh(self, interval_ms: int = REFRESH_INTERVAL_MS) -> Optional[str]:
        """Begin redrawing on a timer, so clocks and quests keep up on their own.

        Args:
            interval_ms: How often to redraw, in milliseconds.

        Returns:
            Optional[str]: The `after` job id, so a caller can cancel the refresh.
        """
        try:
            return self.after(interval_ms, self._auto_refresh)
        except tk.TclError:  # pragma: no cover - the window may already be closing
            return None

    def _auto_refresh(self) -> None:
        """Redraw, then queue the next redraw.

        Returns:
            None
        """
        try:
            self.refresh()
            self.after(REFRESH_INTERVAL_MS, self._auto_refresh)
        except tk.TclError:  # pragma: no cover - the window may already be closing
            return


#: Czech alias for `PlayerGameView`, as `PRD.md` section 5 and `HracGameView` in the diagram
#: require.
HracGameView = PlayerGameView
