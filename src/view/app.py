"""The application window.

`build_application` is the only place that decides what the window contains. It assembles the
controller stack — a configuration, a game manager driven by it, and the window controller
that turns clicks into moves — and hands the window to the view.

The view proper arrives in the view layer; until then this draws the board state it can and
says plainly what is missing rather than pretending to be the finished window.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from controller.controller import GameController
from controller.window_controller import WindowController
from model.game.configuration import load_configuration
from model.game.games import DEFAULT_GAME

APPLICATION_TITLE = "ChessWithQuests"


def build_application(root: tk.Tk, game: str = DEFAULT_GAME) -> tk.Tk:
    """Build the application window on a Tk root and return it.

    Args:
        root: The `tkinter.Tk` instance to build into.
        game: Name of the configuration to start. Defaults to `chess`.

    Returns:
        tkinter.Tk: The same root, configured and ready for `mainloop`, carrying the
        assembled `WindowController` as `root.window_controller`.
    """
    root.title(f"{APPLICATION_TITLE} - {game}")

    style = ttk.Style(root)
    style.theme_use(style.theme_names()[0])

    # The window is driven by a real game, not a placeholder: the configuration supplies the
    # board and the rules, and everything below this line is that game being played.
    controller = WindowController(game_controller=GameController())
    controller.start()
    root.window_controller = controller  # type: ignore[attr-defined]

    frame = ttk.Frame(root, padding=24)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=APPLICATION_TITLE, font=("TkDefaultFont", 20)).pack(pady=(0, 8))
    ttk.Label(frame, text=f"Configuration: {game}").pack(pady=(0, 8))

    manager = controller.game_controller.game_manager
    _draw_board(frame, manager)

    ttk.Label(frame, text=controller.status_message).pack(pady=(8, 0))
    return root


def _draw_board(parent: tk.Misc, manager: object) -> None:
    """Draw the position the game manager is holding.

    Args:
        parent: The widget to draw into.
        manager: The `GameManager` whose board and active player are shown.

    Returns:
        None
    """
    board = manager.board  # type: ignore[attr-defined]
    grid = ttk.Frame(parent)
    grid.pack(pady=(8, 8))

    for row in range(board.rows):
        for col in range(board.cols):
            piece = board.get_piece_at((row, col))
            glyph = piece.getSymbol() if piece is not None else "·"
            ttk.Label(
                grid,
                text=glyph,
                width=3,
                anchor="center",
                font=("TkDefaultFont", 18),
            ).grid(row=row, column=col)


def build_game(game: str = DEFAULT_GAME) -> Optional[object]:
    """Load a configuration by name, for a caller that wants the game without the window.

    Args:
        game: Name of the configuration to load.

    Returns:
        Optional[object]: The loaded configuration.
    """
    return load_configuration(game)
