"""The settings form.

One renderer, driven by what the configuration and its rules declare. A rule says what may be
configured about it by declaring fields; this form asks for those fields and nowhere else, so a
new rule is configurable the moment it is written and no form has to learn its name.

The form edits a copy. Nothing a player does here reaches the game until they save, and
cancelling leaves the game exactly as it was.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

#: The kinds of field the form knows how to ask for, and what widget each gets.
_WIDGETS = {
    "text": "entry",
    "integer": "entry",
    "number": "entry",
    "boolean": "checkbutton",
    "choice": "combobox",
}


class SettingsDialog:
    """A form over the fields a configuration's rules declare."""

    def __init__(
        self,
        master: tk.Misc,
        configuration: Any,
        on_saved: Optional[Callable[[Any], None]] = None,
    ):
        """Build the form.

        Args:
            master: The window the dialog belongs to.
            configuration: The `Configuration` whose rules and values are being edited.
            on_saved: Called with the configuration once the player saves.
        """
        self.configuration = configuration
        self.on_saved = on_saved
        self.editors: Dict[str, Any] = {}
        self.sections: List[ttk.LabelFrame] = []

        self.window = tk.Toplevel(master)
        self.window.title(f"Settings — {configuration.name}")
        self.window.transient(master)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)
        self.window.bind("<Escape>", lambda _event: self.cancel())

        body = ttk.Frame(self.window, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(
            body,
            text=f"{configuration.name}: {len(configuration.enabled_rules())} rules in force",
            font=("TkDefaultFont", 13, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True)
        self._build(notebook)

        buttons = ttk.Frame(body)
        buttons.pack(pady=(12, 0))
        ttk.Button(buttons, text="Save", command=self.save, width=10).pack(side="left", padx=4)
        ttk.Button(buttons, text="Reset", command=self.reset, width=10).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.cancel, width=10).pack(side="left", padx=4)

    def _build(self, notebook: ttk.Notebook) -> None:
        """Build one tab per rule that declares anything configurable.

        Args:
            notebook: The notebook to fill.

        Returns:
            None
        """
        by_rule: Dict[str, List[Any]] = {}
        for rule in self.configuration.enabled_rules():
            try:
                fields = rule.value_fields()
            except Exception:  # pragma: no cover - a rule may not declare fields
                fields = []
            if fields:
                by_rule.setdefault(rule.default_name, fields)

        if not by_rule:
            ttk.Label(notebook, text="This game declares nothing to configure.").pack()
            return

        for name, fields in by_rule.items():
            page = ttk.Frame(notebook, padding=10)
            notebook.add(page, text=name)
            frame = ttk.LabelFrame(page, text=name, padding=8)
            frame.pack(fill="both", expand=True)
            self.sections.append(frame)
            for row, field in enumerate(fields):
                self._add_field(frame, row, field)

    def _add_field(self, frame: ttk.LabelFrame, row: int, field) -> None:
        """Add one declared field to the form.

        Args:
            frame: The tab to add it to.
            row: The row to put it on.
            field: The `Field` declaring the value.

        Returns:
            None
        """
        ttk.Label(frame, text=field.label or field.name).grid(row=row, column=0, sticky="w", pady=3)
        kind = getattr(field, "kind", "text")
        variable = tk.StringVar(value=str(getattr(field, "default", "")))
        self.editors[field.name] = variable

        widget_kind = _WIDGETS.get(kind, "entry")
        if widget_kind == "checkbutton":
            variable = tk.BooleanVar(value=bool(getattr(field, "default", False)))
            self.editors[field.name] = variable
            ttk.Checkbutton(frame, text="on", variable=variable).grid(row=row, column=1, sticky="w")
            return
        if widget_kind == "combobox":
            choices = [str(choice) for choice in (getattr(field, "choices", None) or [])]
            widget = ttk.Combobox(
                frame, textvariable=variable, values=choices, state="readonly", width=28
            )
        else:
            widget = ttk.Entry(frame, textvariable=variable, width=30)
        widget.grid(row=row, column=1, sticky="w", pady=3)
        if field.help:
            ttk.Label(frame, text=field.help, foreground="#666").grid(row=row, column=2, sticky="w")

    def values(self) -> Dict[str, Any]:
        """Return the values the form currently shows.

        Returns:
            Dict[str, Any]: The declared field names and what was typed into them.
        """
        collected: Dict[str, Any] = {}
        for name, variable in self.editors.items():
            raw = variable.get()
            if isinstance(raw, bool):
                collected[name] = raw
                continue
            try:
                collected[name] = int(raw)
            except (TypeError, ValueError):
                collected[name] = raw
        return collected

    def save(self) -> None:
        """Apply the form's values to the configuration and close.

        Returns:
            None
        """
        collected = self.values()
        for rule in self.configuration.enabled_rules():
            for field in rule.value_fields():
                if field.name in collected:
                    rule.value[field.name] = collected[field.name]
        self.close()
        if self.on_saved is not None:
            self.on_saved(self.configuration)

    def reset(self) -> None:
        """Put every field back to the value its declaration names.

        Returns:
            None
        """
        for rule in self.configuration.enabled_rules():
            for field in rule.value_fields():
                variable = self.editors.get(field.name)
                if variable is not None:
                    variable.set(str(getattr(field, "default", "")))

    def cancel(self) -> None:
        """Close without applying anything.

        Returns:
            None
        """
        self.close()

    def close(self) -> None:
        """Release the grab and destroy the dialog.

        Returns:
            None
        """
        try:
            self.window.grab_release()
        except tk.TclError:  # pragma: no cover - the grab may already be gone
            pass
        self.window.destroy()

    def wait(self) -> Optional[str]:
        """Hold the dialog open until it is answered.

        Returns:
            Optional[str]: `saved` or `cancelled`.
        """
        self.window.wait_window()
        return None
