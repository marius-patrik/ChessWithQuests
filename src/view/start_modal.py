"""The window that asks how you want to play.

Starting the program shows this rather than a board: a game is a configuration, and which one
is a choice the player makes rather than a default the program picks for them. The modal is the
only place that choice is offered.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional


class StartModal:
    """A modal dialog offering the shipped configurations, settings, and Start."""

    def __init__(
        self,
        master: tk.Misc,
        games: List[str],
        default: str,
        on_start: Callable[[str], None],
        on_settings: Optional[Callable[[], None]] = None,
    ):
        """Build the modal.

        Args:
            master: The window the modal belongs to.
            games: The names of the configurations that can be played.
            default: The configuration selected when the modal opens.
            on_start: Called with the chosen configuration's name.
            on_settings: Called when the player asks for the settings form.
        """
        self.on_start = on_start
        self.on_settings = on_settings
        self.choice = tk.StringVar(
            value=default if default in games else (games[0] if games else "")
        )

        self.window = tk.Toplevel(master)
        self.window.title("New game")
        self.window.transient(master)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        body = ttk.Frame(self.window, padding=20)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="ChessWithQuests", font=("TkDefaultFont", 18, "bold")).pack(
            pady=(0, 4)
        )
        ttk.Label(body, text="Choose a game to play.").pack(pady=(0, 14))

        self.selector = ttk.Combobox(
            body, textvariable=self.choice, values=games, state="readonly", width=28
        )
        self.selector.pack(pady=(0, 18))

        buttons = ttk.Frame(body)
        buttons.pack()

        self.start_button = ttk.Button(buttons, text="Start", command=self.start, width=12)
        self.start_button.pack(side="left", padx=(0, 8))
        self.start_button.bind("<Return>", lambda _event: self.start())

        if on_settings is not None:
            self.settings_button = ttk.Button(
                buttons, text="Settings", command=self._open_settings, width=12
            )
            self.settings_button.pack(side="left")

        ttk.Button(body, text="Cancel", command=self.close).pack(pady=(18, 0))

        self.selector.focus_set()
        self.window.update_idletasks()
        self._centre(master)

    def _centre(self, master: tk.Misc) -> None:
        """Put the modal in the middle of the window it belongs to.

        Args:
            master: The window the modal belongs to.

        Returns:
            None
        """
        try:
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            x = master.winfo_rootx() + (master.winfo_width() - width) // 2
            y = master.winfo_rooty() + (master.winfo_height() - height) // 2
            self.window.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except tk.TclError:  # pragma: no cover - depends on the window manager
            return

    def _open_settings(self) -> None:
        """Show the settings form without dismissing the modal.

        Returns:
            None
        """
        if self.on_settings is not None:
            self.on_settings()

    def start(self) -> None:
        """Hand the chosen configuration to the caller and close the modal.

        Returns:
            None
        """
        chosen = self.choice.get()
        self.close()
        self.on_start(chosen)

    def close(self) -> None:
        """Close the modal without starting anything.

        Returns:
            None
        """
        try:
            self.window.grab_release()
        except tk.TclError:  # pragma: no cover - the grab may already be gone
            pass
        self.window.destroy()

    def wait(self) -> None:
        """Hold the modal open until it is answered.

        Returns:
            None
        """
        self.window.wait_window()
