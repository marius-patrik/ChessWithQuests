"""The application window.

`build_application` is the only place that decides what the window contains and what order it
appears in: the start modal first, because choosing a game is the player's decision, and the
board second. It assembles the controller stack and hands the window to the view.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from controller.controller import GameController
from controller.window_controller import WindowController
from model.game.configuration import load_configuration
from model.game.games import DEFAULT_GAME, available_games
from model.game.manager import GameManager
from view.player_game_view import PlayerGameView
from view.start_modal import StartModal

APPLICATION_TITLE = "ChessWithQuests"


def build_application(root: tk.Tk, game: str = DEFAULT_GAME, show_modal: bool = True) -> tk.Tk:
    """Build the application window on a Tk root and return it.

    Args:
        root: The `tkinter.Tk` instance to build into.
        game: Name of the configuration to start with.
        show_modal: Whether to ask which game to play before showing the board. False starts
            straight into `game`, which is what a caller driving the window from a test wants.

    Returns:
        tkinter.Tk: The same root, carrying the assembled `PlayerGameView` as
        `root.game_view` and its `WindowController` as `root.window_controller`.
    """
    root.title(f"{APPLICATION_TITLE} - {game}")
    style = ttk.Style(root)
    style.theme_use(style.theme_names()[0])

    games = available_games()
    controller = WindowController(
        game_controller=GameController(GameManager(configuration=load_configuration(game)))
    )
    controller.start()

    shell = ttk.Frame(root, padding=0)
    shell.pack(fill="both", expand=True)
    root.game_view = PlayerGameView(shell, controller)  # type: ignore[attr-defined]
    root.game_view.pack(fill="both", expand=True)
    root.window_controller = controller  # type: ignore[attr-defined]
    root.available_games = games  # type: ignore[attr-defined]

    if show_modal:
        root.after(50, lambda: _offer_modal(root, games, controller))
    return root


def _offer_modal(root: tk.Tk, games: List[str], controller: WindowController) -> None:
    """Ask which game to play, and switch the window to the answer.

    Args:
        root: The window the modal belongs to.
        games: The configurations that can be played.
        controller: The controller whose game the modal replaces.

    Returns:
        None
    """
    chosen: List[str] = []

    def start(game: str) -> None:
        """Replace the running game with the chosen configuration.

        Args:
            game: The configuration to play.

        Returns:
            None
        """
        chosen.append(game)
        manager = GameManager(configuration=load_configuration(game))
        controller.game_controller.game_manager = manager
        controller.set_status(f"Playing {game}.")
        root.game_view.reload(manager)  # type: ignore[attr-defined]

    StartModal(
        root,
        games=games,
        default=DEFAULT_GAME,
        on_start=start,
        on_settings=lambda: controller.show_dialog("Settings arrive with the settings form."),
    )
