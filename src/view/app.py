"""The application window.

`build_application` is the only place that decides what the window contains. The game
view built by the view layer takes over from the placeholder below as soon as it lands;
until then this is the smallest thing that is honestly a window.
"""

import tkinter as tk
from tkinter import ttk

from model.game.games import DEFAULT_GAME

APPLICATION_TITLE = "ChessWithQuests"


def build_application(root: tk.Tk, game: str = DEFAULT_GAME) -> tk.Tk:
    """Build the application window on a Tk root and return it.

    Args:
        root: The `tkinter.Tk` instance to build into.
        game: Name of the configuration to start. Defaults to `chess`.

    Returns:
        tkinter.Tk: The same root, configured and ready for `mainloop`.
    """
    root.title(f"{APPLICATION_TITLE} - {game}")

    style = ttk.Style(root)
    style.theme_use(style.theme_names()[0])

    frame = ttk.Frame(root, padding=24)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text=APPLICATION_TITLE, font=("TkDefaultFont", 20)).pack(pady=(0, 8))
    ttk.Label(frame, text=f"Configuration: {game}").pack(pady=(0, 8))
    ttk.Label(frame, text="The game view arrives in the view layer.").pack()

    return root
