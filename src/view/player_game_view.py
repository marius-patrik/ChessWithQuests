"""The whole game, on screen.

`PlayerGameView` is the window's arrangement: both player panels, the board, the turn
indicator, the move history, the quest cards and the status footer. It owns the refresh and
nothing else — every click goes to the controller and every redraw reads the model.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, Tuple

from controller.window_controller import WindowController
from model.game.manager import GameManager
from model.game.move import Move
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

#: The smallest a board square is drawn, in pixels.
#:
#: Below this the piece glyph and its coordinate labels stop being legible, so a window too short
#: to hold a board this size loses the board rather than shrinking it into unreadability. This is
#: the floor the fit calculation stops at, not a promise that everything fits at every size.
MIN_SQUARE_SIZE = 24

#: The state a game can be in, and what the footer says about it.
STATE_LABELS = {
    GameManager.STATE_TIMEOUT: "Time is up.",
    GameManager.STATE_CHECKMATE: "Checkmate.",
    GameManager.STATE_STALEMATE: "Stalemate — the game is drawn.",
    GameManager.STATE_CHECK: "Check.",
    GameManager.STATE_IN_PROGRESS: "",
}

#: The one reason that means the game ended in checkmate.
#:
#: Every other decisive `Result.reason` is a different ending that happens to arrive while the
#: state constants say something generic: a chess game lost on time is a flag fall, and an English
#: draughts game is won by immobilisation — a game with no king and no check, where "checkmate" is
#: not a thing that could have happened. The reason is the only field that says which ending it
#: was, so the sentence is built from it rather than from the state.
CHECKMATE_REASON = "checkmate"


def outcome_sentence(result: Any) -> str:
    """Say how a finished game ended, in one sentence, without claiming more than happened.

    Args:
        result: The finished game's `Result`, carrying `winner` and `reason`.

    Returns:
        str: The sentence for the footer. A draw names its reason; a decisive result names the
        winning colour and the reason; only a reason of `"checkmate"` is called a checkmate.
    """
    reason = str(getattr(result, "reason", "") or "").strip()
    winner = getattr(result, "winner", None)
    if winner is None:
        return f"Draw — {reason}." if reason else "Draw."
    colour = "White" if winner == 1 else "Black"
    if reason == CHECKMATE_REASON:
        return f"Checkmate — {colour} wins."
    return f"{colour} wins — {reason}."


def move_label(notation: Optional[Any], number: int, move: Move) -> str:
    """Return the text the move history lists a move as.

    The naming is the configuration's: `notation` is whatever `Configuration.notation` holds,
    and a configuration that declares none gets a coordinate pair. The engine holds no naming
    of its own, so falling back to coordinates is saying nothing at all — where the view used
    to reach into a game for the naming, which drew every game, copies included, in that one
    game's letters.

    Args:
        notation: The configuration's naming, or None when it declares none.
        number: The move's number in the game, counted from one.
        move: The `Move` to label.

    Returns:
        str: The label for the move list.
    """
    if notation is not None:
        return notation.move_label(number, move)
    start, end = move.start_pos, move.end_pos
    return f"{number}. ({start[0]}, {start[1]}) – ({end[0]}, {end[1]})"


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

        self.max_square_size = square_size
        self._build_layout(square_size)
        self.refresh()
        # `pack` gives a child leftover space only if there is leftover space, and `body` holds
        # `expand=True`, so on a short window the board column was given nothing at all and Tk
        # unmapped the bottom panel without a word. The board is the only part of the window whose
        # size is a choice rather than a requirement, so it is the part that gives way.
        self.bind("<Configure>", self._on_resize)

    def _build_layout(self, square_size: int) -> None:
        """Place every widget.

        Args:
            square_size: The width and height of one board square, in pixels.

        Returns:
            None
        """
        heading = ttk.Frame(self)
        heading.pack(fill="x")
        self._heading = heading
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

        self._turn_label = ttk.Label(left, textvariable=self.turn, font=("TkDefaultFont", 12))
        self._turn_label.pack(anchor="w")
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
            # which takes all the slack.
            #
            # This comment used to claim that packing it there also fixed the panel "squeezed to
            # nothing and silently stopped appearing" on a short window. It did not: `pack` gives
            # a child the height it asks for and unmaps whatever is left over, and `body` holds
            # `expand=True`, so on any window shorter than about 760 pixels this panel was not
            # drawn at all — `winfo_ismapped()` was 0, not a small number. `fit_board` is what
            # actually fixed it: the board is the only thing here whose size is a choice, so it
            # is the thing that gives way.
            self.bottom_player.pack(fill="x")

        right = ttk.Frame(body, padding=(12, 0))
        right.pack(side="left", fill="both", expand=True)

        # Laid out with grid rather than pack, because pack hands every child the height it asked
        # for and unmaps whatever is left over. Both panels here want more than a short window has,
        # so pack silently dropped the move history. grid distributes the height that actually
        # exists between the two rows that can use it, and both stay on screen.
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Quests", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.quest_list = QuestList(right, self.manager.quest_manager)
        self.quest_list.grid(row=1, column=0, sticky="nsew")

        ttk.Label(right, text="Moves", font=("TkDefaultFont", 12, "bold")).grid(
            row=2, column=0, sticky="w"
        )
        self.history = tk.Listbox(right, height=1, width=28)
        self.history.grid(row=3, column=0, sticky="nsew")

        self.status_label = ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w")
        self.status_label.pack(fill="x", pady=(8, 0))
        self._left = left

    def _on_resize(self, _event: Optional[tk.Event] = None) -> None:
        """Fit the board to whatever height the window now has.

        Args:
            _event: The `<Configure>` event, unused — the widget already knows its own size.

        Returns:
            None
        """
        self.fit_board()
        self.fit_quest_cards()

    def available_board_height(self) -> int:
        """Return the height the board may occupy without squeezing any panel out of existence.

        Every other widget in the window is packed with `fill="x"` and none of them has
        `expand=True`, so each keeps the height it asks for. The board is the one child whose size
        is a preference, so it absorbs the difference.

        Returns:
            int: Pixels available for the board, never negative.
        """
        if not hasattr(self, "board_view"):
            return 0
        total = self.winfo_height()
        if total <= 1:
            # Before the first map, Tk reports 1 rather than nothing. Measuring now would fit the
            # board to a one-pixel window, so the caller is told there is nothing to decide yet.
            return 0
        fixed = [self._heading, self._turn_label, self.status_label]
        for panel in (self.top_player, self.bottom_player):
            if panel is not None:
                fixed.append(panel)
        used = sum(widget.winfo_reqheight() for widget in fixed)
        # The board's own padding, the frame's padding, and the gap under the turn label.
        used += 24
        return max(0, total - used)

    def fit_board(self) -> None:
        """Shrink or restore the board so every panel stays on screen.

        The square size is never made larger than the window was built with, so a tall window gets
        the original board rather than an enormous one, and never smaller than
        `MIN_SQUARE_SIZE`, at which point the window is simply too short to hold everything.

        Returns:
            None
        """
        available = self.available_board_height()
        if available <= 0:
            return
        rows = max(1, self.manager.board.rows)
        wanted = min(self.max_square_size, available // rows)
        wanted = max(MIN_SQUARE_SIZE, wanted)
        if wanted == self.board_view.square_size:
            return
        self.board_view.square_size = wanted
        self.board_view.refresh(self.manager.board)

    def fit_quest_cards(self) -> None:
        """Show as many quest cards as the window has room for.

        Six cards ask for more height than a short window has, and grid answers an over-long column
        by collapsing the rows at the bottom of it — which is how the move history used to
        disappear. The cards are the part of the column that is a choice: the roster is not shorter
        for having less of it shown.

        The budget comes from the window's own height rather than from the quest column's, because
        `<Configure>` fires before the layout has settled and the column still reports the height
        it had at the previous size. Reading it there would decide on the old window.

        Returns:
            None
        """
        total = self.winfo_height()
        if total <= 1:
            return
        fixed = [self._heading, self._turn_label, self.status_label]
        for panel in (self.top_player, self.bottom_player):
            if panel is not None:
                fixed.append(panel)
        used = sum(widget.winfo_reqheight() for widget in fixed) + 24
        cards = self.quest_list.winfo_children()
        card_height = cards[0].winfo_reqheight() if cards else 56
        # What the column keeps back: the "Quests" and "Moves" headings, the gap between them, and
        # at least a couple of rows of history.
        history_min = self.history.winfo_reqheight() + 48
        budget = total - used - history_min
        limit = max(1, min(6, budget // max(card_height, 1)))
        if limit != self.quest_list.limit:
            self.quest_list.limit = limit
            self.quest_list.rebuild()

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
        if state in TERMINAL_STATES:
            result = self.manager.result
            if result is not None:
                # The reason, not the state, says what happened: a flag fall and an
                # immobilisation both arrive while the state says something generic, and neither
                # is a checkmate.
                label = outcome_sentence(result)
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
        notation = self.manager.configuration.notation if self.manager.configuration else None
        for number, move in enumerate(moves, start=1):
            # Notated rather than printed as coordinates, because the configuration's own
            # naming is the same one its transcript is written with: the list and the export
            # cannot disagree, and a variant that renames its squares renames both.
            self.history.insert("end", move_label(notation, number, move))

    def _quit(self) -> None:
        """Close the window.

        Returns:
            None
        """
        self.stop_auto_refresh()
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
            self._refresh_job_id = self.after(interval_ms, self._auto_refresh)
            return self._refresh_job_id
        except tk.TclError:  # pragma: no cover - the window may already be closing
            return None

    def _auto_refresh(self) -> None:
        """Charge the player to move, redraw, then queue the next pass.

        The charge is what makes a clock a clock: the manager times a turn from a monotonic
        reading, but only when it is asked, and nothing was asking. So the clock stood still
        while the window was open and a player thought, and moved when they finally clicked.

        Returns:
            None
        """
        try:
            if self.manager.get_state() in (GameManager.STATE_IN_PROGRESS, GameManager.STATE_CHECK):
                self.manager.charge_turn()
            self.refresh()
            self.after(REFRESH_INTERVAL_MS, self._auto_refresh)
        except tk.TclError:  # pragma: no cover - the window may already be closing
            return

    def stop_auto_refresh(self) -> None:
        """Stop redrawing on a timer.

        Returns:
            None
        """
        self._refresh_job = None
        for job in (getattr(self, "_refresh_job_id", None),):
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:  # pragma: no cover - the job may already be gone
                    pass
        self._refresh_job_id = None


#: Czech alias for `PlayerGameView`, as `PRD.md` section 5 and `HracGameView` in the diagram
#: require.
HracGameView = PlayerGameView
