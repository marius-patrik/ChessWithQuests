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
from model.game.configuration import load_configuration, load_default_configuration
from model.game.games import available_games
from model.game.manager import GameManager
from view.player_game_view import PlayerGameView
from view.settings_dialog import SettingsDialog
from view.start_modal import StartModal

APPLICATION_TITLE = "ChessWithQuests"


def build_application(root: tk.Tk, game: Optional[str] = None, show_modal: bool = True) -> tk.Tk:
    """Build the application window on a Tk root and return it.

    Args:
        root: The `tkinter.Tk` instance to build into.
        game: Name of the configuration to start with. Defaults to None, which plays the
            configuration the installed `games/` declares as its default — a name the engine
            holds no opinion about, and one this module therefore has no default argument for.
        show_modal: Whether to ask which game to play before showing the board. False starts
            straight into `game`, which is what a caller driving the window from a test wants.

    Returns:
        tkinter.Tk: The same root, carrying the assembled `PlayerGameView` as
        `root.game_view` and its `WindowController` as `root.window_controller`.
    """
    # Resolved once, here, and the resolved name is what the window is titled with and what the
    # start modal offers as its default — a name the window had to ask for is a name it would
    # otherwise have to ask for twice.
    configuration = load_configuration(game) if game else load_default_configuration()
    game = configuration.name
    root.title(f"{APPLICATION_TITLE} - {game}")
    style = ttk.Style(root)
    style.theme_use(style.theme_names()[0])

    games = available_games()
    controller = WindowController(
        game_controller=GameController(GameManager(configuration=configuration))
    )
    controller.start()

    shell = ttk.Frame(root, padding=0)
    shell.pack(fill="both", expand=True)

    view = PlayerGameView(
        shell,
        controller,
        on_settings=lambda: open_settings(root, controller),
        on_new_game_request=lambda: _offer_modal(root, games, controller, game),
    )
    view.pack(fill="both", expand=True)
    root.game_view = view  # type: ignore[attr-defined]
    root.window_controller = controller  # type: ignore[attr-defined]
    root.available_games = games  # type: ignore[attr-defined]
    # The clock runs on real time, so something has to ask for it. Nothing was, and a clock
    # that only moved when a player clicked was not a clock.
    view.start_auto_refresh()

    if show_modal:
        root.after(50, lambda: _offer_modal(root, games, controller, game))
    return root


def open_settings(root: tk.Tk, controller: WindowController) -> SettingsDialog:
    """Open the settings form over the game being played.

    The form is pointed at the shipped `games/` directory, which is where the corner selector
    reads the configurations it offers from and where creating, renaming and deleting write.
    A caller driving the window from a test passes its own root so the shipped directory is
    left alone.

    Args:
        root: The window the form belongs to.
        controller: The controller whose game is being configured.

    Returns:
        SettingsDialog: The form, so a caller can wait on it.
    """
    configuration = controller.game_controller.game_manager.configuration
    dialog = SettingsDialog(
        root,
        configuration,
        on_saved=lambda saved: (
            controller.set_status(f"{saved.name} settings saved."),
            root.game_view.refresh(),
        ),
        root=getattr(root, "games_root", None),
    )
    root.settings_dialog = dialog  # type: ignore[attr-defined]
    return dialog


def _offer_modal(
    root: tk.Tk, games: List[str], controller: WindowController, default: Optional[str] = None
) -> None:
    """Ask which game to play, and switch the window to the answer.

    Args:
        root: The window the modal belongs to.
        games: The configurations that can be played.
        controller: The controller whose game the modal replaces.
        default: The configuration the modal offers as its choice, which is the one the game
            being played came from. Defaults to None, which offers the first of `games`.

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
        default=default,
        on_start=start,
        on_settings=lambda: open_settings(root, controller),
    )
