"""The code editor: where a rule's logic is actually written.

A configuration's rules and quests are Python files, and this is where they are edited. It is
a plain text area over one file in the configuration directory being edited, and it is the
only place in the product where a player writes code.

Nothing here decides whether code is good. `model.game.source_validation` does that, before
the file is written: this editor refuses to save a file the check refuses, and shows what the
check said. Saving first and finding out at game start would put the failure in the middle of
a game, which is the one place a player cannot act on it.

The bound from `PRD.md` section 3.3 holds here as it holds everywhere: a file may be opened
only inside the configuration directory this editor was opened for. `open_source` refuses
anything else rather than trusting its caller.
"""

import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional

from model.game.source_validation import SourceReport, validate_source

#: Where the file list, the text area and the verdict sit in the editor.
TEXT_WIDTH = 96
TEXT_HEIGHT = 30


class CodeEditor:
    """A window editing one Python file in a configuration directory."""

    def __init__(
        self,
        master: tk.Misc,
        path: str,
        kind: str = "rule",
        package: str = "",
        root: Optional[str] = None,
        readonly_reason: Optional[str] = None,
        on_saved: Optional[Callable[[str], None]] = None,
    ):
        """Build the editor over a file.

        Args:
            master: The window the editor belongs to.
            path: The file to edit. It must be inside `root`.
            kind: `"rule"` to hold the file to the rule interface, `"quest"` for the quest one.
            package: The configuration's registered module name, so a relative import inside
                the file resolves while the code is checked.
            readonly_reason: When set, the editor refuses every save and says why. The
                default configuration is protected this way as well as by the form, so the
                guard does not depend on which door the editor was opened through.
            root: The configuration directory. Defaults to the file's grandparent, which is
                what a file in `rules/` or `quests/` has.
            on_saved: Called with the path after a save that passed the check.

        Raises:
            ValueError: If `path` is not inside `root`. Loading player-authored code from an
                arbitrary path is exactly what the bound is for.
        """
        self.path = os.path.abspath(path)
        self.kind = kind
        self.package = package
        self.root = os.path.abspath(root or os.path.dirname(os.path.dirname(self.path)))
        self.readonly_reason = readonly_reason
        if not self._within(self.path, self.root):
            raise ValueError(
                f"{self.path} is outside {self.root}; only files in the "
                f"configuration being edited may be opened"
            )
        self.on_saved = on_saved
        self.report: Optional[SourceReport] = None
        self.dirty = False

        self.window = tk.Toplevel(master)
        self.window.title(f"Edit logic — {os.path.basename(self.path)}")
        self.window.transient(master)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        body = ttk.Frame(self.window, padding=12)
        body.pack(fill="both", expand=True)

        self.text = tk.Text(body, width=TEXT_WIDTH, height=TEXT_HEIGHT, wrap="none", undo=True)
        self.text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scroll.set)
        self.text.bind("<Control-s>", lambda _event: self.save())
        self.text.bind("<KeyRelease>", self._mark_dirty)

        self.verdict = tk.StringVar(value="")
        ttk.Label(
            self.window, textvariable=self.verdict, wraplength=TEXT_WIDTH, justify="left"
        ).pack(fill="x", padx=12)

        buttons = ttk.Frame(self.window, padding=12)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Check", command=self.check, width=10).pack(side="left", padx=4)
        ttk.Button(buttons, text="Save", command=self.save, width=10).pack(side="left", padx=4)
        ttk.Button(buttons, text="Close", command=self.close, width=10).pack(side="right")

        self.load()

    @staticmethod
    def _within(candidate: str, directory: str) -> bool:
        """Report whether a path lies inside a directory.

        Args:
            candidate: The absolute path to test.
            directory: The absolute containing directory.

        Returns:
            bool: True when `candidate` is inside `directory` or is it.
        """
        try:
            return os.path.commonpath([candidate, directory]) == directory
        except ValueError:  # pragma: no cover - different drives on Windows
            return False

    def load(self) -> str:
        """Read the file into the text area, replacing anything already there.

        Returns:
            str: The file's text, or "" when the file does not exist yet. A file the editor
            is about to create reads as empty rather than as an error.
        """
        try:
            with open(self.path, encoding="utf-8") as handle:
                source = handle.read()
        except FileNotFoundError:
            source = ""
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", source)
        self.text.edit_modified(False)
        self.dirty = False
        return source

    def source(self) -> str:
        """Return what the text area currently holds.

        Returns:
            str: The code as the player has it.
        """
        return self.text.get("1.0", tk.END)

    def _mark_dirty(self, _event: Optional[tk.Event] = None) -> None:
        """Record that the text has changed since it was last checked.

        Args:
            _event: The key event, unused.

        Returns:
            None
        """
        self.dirty = True

    def check(self) -> SourceReport:
        """Check the code in the text area, and say what the check found.

        Returns:
            SourceReport: The verdict, also recorded on `self.report`.
        """
        self.report = validate_source(
            self.source(), self.path, kind=self.kind, package=self.package
        )
        self.verdict.set(self.report.message())
        return self.report

    def save(self) -> Optional[str]:
        """Write the file, but only if it passes the check.

        Returns:
            Optional[str]: The path written, or None when the code was refused and nothing
            was written. Returning rather than raising is deliberate: refusing is the ordinary
            outcome of editing code, not an exceptional one.
        """
        if self.readonly_reason:
            self.verdict.set(self.readonly_reason)
            return None
        report = self.check()
        if not report.ok:
            return None
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(self.source())
        self.text.edit_modified(False)
        self.dirty = False
        if self.on_saved is not None:
            self.on_saved(self.path)
        return self.path

    def close(self) -> None:
        """Destroy the editor window.

        Returns:
            None
        """
        try:
            self.window.destroy()
        except tk.TclError:  # pragma: no cover - the window may already be gone
            return


def editable_sources(configuration_path: str, section: str) -> List[str]:
    """Return the files in a configuration section that a player may edit.

    A section holds the modules the configuration brought with it. `__init__.py` is left out
    of nothing — it is a real file and a player may edit it — but a module that declares no
    rule is not somewhere the editor should offer to change a rule.

    Args:
        configuration_path: The configuration's directory.
        section: The subdirectory name, for example `rules`.

    Returns:
        List[str]: Absolute paths to the `.py` files in the section, sorted by name.
    """
    directory = os.path.join(configuration_path, section)
    if not os.path.isdir(directory):
        return []
    return sorted(
        os.path.join(directory, name) for name in os.listdir(directory) if name.endswith(".py")
    )
