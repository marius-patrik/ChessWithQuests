"""The settings surface.

One renderer, driven by what the configuration declares. A board declares its rows and columns,
a piece declares its name and symbols, a rule declares what may be configured about it, a quest
declares its parameters and a clock declares its time control. This form asks for all of that
and nothing else, so a new rule is configurable the moment it is written and no form has to
learn its name.

Five sections, one per configurable surface, and a selector in the corner saying *which*
configuration is being edited — here and nowhere else. The start modal is where a player
chooses a game to play; if editing could silently change what is about to be played, the two
decisions would be one, and a player who meant to try a variant would find themselves in one.

The Rules and Quests sections also open the code editor, because a rule's logic is code and
there is no way to express it in a form. FR-32 makes the *data* form-exposed; FR-33 says so
expressly, and a rule that forbade every move cannot be written as a field.
"""

import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from model.game.clock_fields import apply_clock_values, clock_fields
from model.game.configuration import (
    Configuration,
    copy_configuration,
    delete_configuration,
    load_configuration,
    load_default_configuration,
    rename_configuration,
)
from model.game.field import Field
from model.game.games import available_games
from view.code_editor import CodeEditor, editable_sources

#: The sections, in the order FR-31 lists them.
SECTIONS = ("Board", "Pieces", "Rules", "Quests", "Clocks")

#: The kinds of field the form knows how to ask for, and what widget each gets.
_WIDGETS = {
    "text": "entry",
    "integer": "entry",
    "decimal": "entry",
    "boolean": "checkbutton",
    "choice": "combobox",
}


class SettingsDialog:
    """The settings form: a corner selector, five sections, and Save, Reset and Cancel."""

    def __init__(
        self,
        master: tk.Misc,
        configuration: Any,
        on_saved: Optional[Callable[[Any], None]] = None,
        root: Optional[str] = None,
    ):
        """Build the form.

        Args:
            master: The window the dialog belongs to.
            configuration: The `Configuration` being edited. It is replaced when the player
                selects another one, so it is read from `self.configuration` everywhere else.
            on_saved: Called with the configuration once the player saves.
            root: The directory configurations live under. Defaults to the shipped `games/`.
        """
        self.configuration = configuration
        self.on_saved = on_saved
        self.root = root
        self.editors: Dict[str, Any] = {}
        self.sections: List[ttk.LabelFrame] = []
        self.entries_by_section: Dict[str, List[Tuple[Any, List[Field], Dict[str, Any]]]] = {
            name: [] for name in SECTIONS
        }
        self.editors_open: List[CodeEditor] = []
        self.message = tk.StringVar(value="")

        self.window = tk.Toplevel(master)
        self.window.title("Settings")
        self.window.transient(master)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)
        self.window.bind("<Escape>", lambda _event: self.cancel())

        body = ttk.Frame(self.window, padding=16)
        body.pack(fill="both", expand=True)

        self._build_selector(body)
        ttk.Label(body, textvariable=self.message, foreground="#8a3b3b").pack(anchor="w")

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill="both", expand=True)
        self._build_sections()

        buttons = ttk.Frame(body)
        buttons.pack(pady=(12, 0))
        ttk.Button(buttons, text="Save", command=self.save, width=10).pack(side="left", padx=4)
        ttk.Button(buttons, text="Reset", command=self.reset, width=10).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=self.cancel, width=10).pack(side="left", padx=4)

    # --- the corner selector

    def _build_selector(self, body: ttk.Frame) -> None:
        """Put the configuration selector in the corner, with a plus button beside it.

        FR-30 says the selector is in the corner and in settings only, and FR-28 says a
        configuration can be created, renamed, duplicated and deleted. The plus button
        duplicates the one being edited, because FR-27 says a variant starts by duplicating the
        default — so duplication is the move that always works, and the name is derived rather
        than asked for.

        Args:
            body: The frame the selector is placed in.

        Returns:
            None
        """
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Configuration:").pack(side="left")

        self.choice = tk.StringVar(value=self.configuration.name)
        self.selector = ttk.Combobox(
            bar,
            textvariable=self.choice,
            values=self.configuration_names(),
            state="readonly",
            width=24,
        )
        self.selector.pack(side="left", padx=6)
        self.selector.bind("<<ComboboxSelected>>", self._selected)

        self.add_button = ttk.Button(bar, text="+", width=3, command=self.add_configuration)
        self.add_button.pack(side="left")
        self.rename_button = ttk.Button(bar, text="Rename", command=self.rename_configuration)
        self.rename_button.pack(side="left", padx=(6, 0))
        self.delete_button = ttk.Button(bar, text="Delete", command=self.delete_configuration)
        self.delete_button.pack(side="left", padx=(6, 0))

    def configuration_names(self) -> List[str]:
        """Return the configurations the selector offers.

        Returns:
            List[str]: Every configuration directory name under `root`, with the one the root
            declares as its default first. `available_games` answers that for any root, so the
            form has no order of its own to keep in step with it.
        """
        return available_games(self.root)

    def _selected(self, _event: Optional[tk.Event] = None) -> Optional[Configuration]:
        """Load the configuration the player chose and rebuild the form over it.

        Args:
            _event: The combobox event, unused.

        Returns:
            Optional[Configuration]: The configuration now being edited, or None when the one
            chosen could not be loaded — in which case the form keeps showing what it had.
        """
        name = self.choice.get()
        if name == self.configuration.name:
            return self.configuration
        try:
            self.configuration = load_configuration(name, root=self.root)
        except (OSError, ValueError) as error:
            self.message.set(f"{name} could not be loaded: {error}")
            self.choice.set(self.configuration.name)
            return None
        self.message.set(_not_in_force(self.configuration))
        self._rebuild()
        return self.configuration

    def add_configuration(self) -> Optional[Configuration]:
        """Duplicate the configuration being edited into a new variant, and edit that.

        FR-27: a variant starts by duplicating the default. Duplicating whatever is being
        edited is the same move one step along, and it is the move that cannot produce a
        variant that still plays the original.

        Returns:
            Optional[Configuration]: The new variant, or None when it could not be created —
            for instance because the name is already taken.
        """
        source = self.configuration.name
        name = _unused_name(source, self.configuration_names())
        try:
            self.configuration = copy_configuration(source, name, root=self.root)
        except (OSError, ValueError) as error:
            self.message.set(f"{name} could not be created: {error}")
            return None
        self.selector.configure(values=self.configuration_names())
        self.choice.set(name)
        self.message.set(f"{name} created from {source}.{_not_in_force(self.configuration)}")
        self._rebuild()
        return self.configuration

    def rename_configuration(self) -> Optional[Configuration]:
        """Rename the configuration being edited.

        Returns:
            Optional[Configuration]: The configuration under its new name, or None when the
            rename was refused. The default configuration refuses, and says so here rather
            than raising.
        """
        name = self.configuration.name
        new_name = _ask(self.window, "Rename configuration", "New name:", f"{name}_2")
        if not new_name or new_name == name:
            return None
        try:
            self.configuration = rename_configuration(name, new_name, root=self.root)
        except (OSError, ValueError, PermissionError) as error:
            self.message.set(str(error))
            return None
        self.selector.configure(values=self.configuration_names())
        self.choice.set(new_name)
        self.message.set(f"{name} renamed to {new_name}.")
        self._rebuild()
        return self.configuration

    def delete_configuration(self) -> Optional[str]:
        """Delete the configuration being edited, and fall back to the default.

        Returns:
            Optional[str]: The name deleted, or None when the deletion was refused. The
            default refuses, which is FR-27, and the form says so rather than raising.
        """
        name = self.configuration.name
        try:
            delete_configuration(name, root=self.root)
        except (OSError, ValueError, PermissionError) as error:
            self.message.set(str(error))
            return None
        # Back to the default rather than to a name this module carries: deleting the last
        # variant leaves nothing else to show, and the configuration a game starts in is the
        # one the root names.
        self.configuration = load_default_configuration(root=self.root)
        self.selector.configure(values=self.configuration_names())
        self.choice.set(self.configuration.name)
        self.message.set(f"{name} deleted.")
        self._rebuild()
        return name

    # --- the sections

    def _build_sections(self) -> None:
        """Build one tab per configurable surface, in the order FR-31 lists them.

        Returns:
            None
        """
        self._build_board_tab()
        self._build_pieces_tab()
        self._build_rules_tab()
        self._build_quests_tab()
        self._build_clocks_tab()

    def _rebuild(self) -> None:
        """Throw away the form and build it again over the configuration now being edited.

        Returns:
            None
        """
        self.editors = {}
        self.sections = []
        self.entries_by_section = {name: [] for name in SECTIONS}
        for tab in self.notebook.tabs():
            # `forget` only takes the page out of the notebook; the widget, its entries and its
            # editors stay alive as children of it. Five rebuilds left thirty children behind,
            # and a player switching configuration a dozen times was holding a hundred live
            # widgets, each with a StringVar and an editor bound to a file that may since have
            # been renamed. A forgotten page has to be destroyed, not just unshown.
            self.notebook.forget(tab)
            self.notebook.nametowidget(tab).destroy()
        self._build_sections()

    def _tab(self, name: str) -> ttk.Frame:
        """Add a tab and return the frame to fill it.

        Args:
            name: The section name, which is also the tab label.

        Returns:
            ttk.Frame: The tab's frame.
        """
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text=name)
        return page

    def _build_board_tab(self) -> None:
        """Build the Board section from what the board declares.

        Returns:
            None
        """
        page = self._tab("Board")
        board = self.configuration.board
        if board is None:
            ttk.Label(page, text="This configuration declares no board.").pack(anchor="w")
            return
        frame = self._frame(page, "Board")
        fields = board.value_fields()
        editors = self._add_fields(frame, fields)
        self.entries_by_section["Board"].append((board, fields, editors))
        ttk.Label(
            page,
            text="Changing the size deals a new board, and ends the game in progress.",
            foreground="#666",
        ).pack(anchor="w")

    def _build_pieces_tab(self) -> None:
        """Build the Pieces section, one frame per piece the configuration offers.

        A configuration offers piece *classes*, and a class is not an instance, so the fields
        are declared from one probe of each class rather than from an object that will be
        played. The frame is labelled with the class it describes, so the form does not claim
        to be editing a running piece.

        Returns:
            None
        """
        page = self._tab("Pieces")
        pieces = self.configuration.pieces
        if not pieces:
            ttk.Label(page, text="This configuration declares no pieces.").pack(anchor="w")
            return
        for index, piece_class in enumerate(pieces):
            probe = _probe(piece_class)
            if probe is None:
                ttk.Label(page, text=f"{piece_class.__name__}: cannot be described.").pack(
                    anchor="w"
                )
                continue
            frame = self._frame(page, piece_class.__name__)
            fields = probe.value_fields()
            editors = self._add_fields(frame, fields)
            # The probe declared the fields; the *class* is what the form edits. Writing to the
            # probe changed nothing that would ever be played, because every piece in a game is
            # built fresh from the class and the class's own constructor arguments decided what it
            # drew. The values now land on the class, so the next piece built carries them.
            self.entries_by_section["Pieces"].append((piece_class, fields, editors))

    def _build_rules_tab(self) -> None:
        """Build the Rules section: a rule's declared fields, and a button to edit its logic.

        Returns:
            None
        """
        page = self._tab("Rules")
        rules = self.configuration.rules
        if not rules:
            ttk.Label(page, text="This configuration declares no rules.").pack(anchor="w")
            return
        for rule in rules:
            frame = self._frame(page, rule.label)
            # `parameters` rather than `value_fields`: the framework adds `enabled` to it, so
            # the switch that turns a rule off is a widget from the same declaration as
            # everything else rather than a hand-built checkbox beside it.
            fields = _rule_parameters(rule)
            editors = self._add_fields(frame, fields)
            self.entries_by_section["Rules"].append((rule, fields, editors))
            for name, variable in editors.items():
                if name in {field.name for field in _safe_fields(rule)}:
                    self.editors.setdefault(name, variable)
            self._add_edit_button(frame, rule, "rule")
        self._add_new_source(page, "rule")

    def _build_quests_tab(self) -> None:
        """Build the Quests section: a quest's parameters, and a button to edit its logic.

        Returns:
            None
        """
        page = self._tab("Quests")
        quests = self.configuration.quests
        if not quests:
            ttk.Label(page, text="This configuration declares no quests.").pack(anchor="w")
            return
        for quest in quests:
            frame = self._frame(page, quest.name)
            fields = _safe_fields(quest)
            editors = self._add_fields(frame, fields)
            self.entries_by_section["Quests"].append((quest, fields, editors))
            self._add_edit_button(frame, quest, "quest")
        self._add_new_source(page, "quest")

    def _build_clocks_tab(self) -> None:
        """Build the Clocks section from what each clock declares.

        Returns:
            None
        """
        page = self._tab("Clocks")
        clocks = self.configuration.clocks
        if not clocks:
            ttk.Label(page, text="This configuration declares no clocks.").pack(anchor="w")
            return
        for clock in clocks:
            name = type(clock).__name__
            frame = self._frame(page, name)
            fields = clock_fields(clock)
            if not fields:
                ttk.Label(frame, text="This clock declares nothing to configure.").pack(anchor="w")
                continue
            editors = self._add_fields(frame, fields)
            self.entries_by_section["Clocks"].append((clock, fields, editors))

    def _frame(self, page: ttk.Frame, title: str) -> ttk.LabelFrame:
        """Add a labelled frame to a tab, and record it as part of the surface.

        Args:
            page: The tab the frame goes in.
            title: The frame's label, which names what it configures.

        Returns:
            ttk.LabelFrame: The new frame.
        """
        frame = ttk.LabelFrame(page, text=title, padding=8)
        frame.pack(fill="x", pady=4)
        self.sections.append(frame)
        return frame

    def _add_fields(self, frame: ttk.LabelFrame, fields: List[Field]) -> Dict[str, Any]:
        """Add a declaration's fields to a frame, one widget each.

        The widgets are returned keyed by field name, and the caller keeps them beside the
        object they configure rather than in one flat dict. That is what makes the Pieces
        section correct: six pieces each declare a `name`, and a single dict keyed by name
        would give six widgets one variable and save the last one's value onto all six.

        Args:
            frame: The frame to add the fields to.
            fields: The declaration.

        Returns:
            Dict[str, Any]: One widget variable per declared field.
        """
        editors: Dict[str, Any] = {}
        for row, field in enumerate(fields):
            editors[field.name] = self._add_field(frame, row, field)
        return editors

    def _add_field(self, frame: ttk.LabelFrame, row: int, field: Field) -> Any:
        """Add one declared field to a frame.

        Args:
            frame: The frame to add the field to.
            row: The row to put it on.
            field: The `Field` declaring the value.

        Returns:
            Any: The widget variable the field is edited through.
        """
        ttk.Label(frame, text=field.label or field.name).grid(row=row, column=0, sticky="w", pady=3)
        kind = getattr(field, "kind", "text")
        default = getattr(field, "default", "")

        widget_kind = _WIDGETS.get(kind, "entry")
        if widget_kind == "checkbutton":
            variable = tk.BooleanVar(value=bool(default))
            ttk.Checkbutton(frame, text="on", variable=variable).grid(row=row, column=1, sticky="w")
        else:
            variable = tk.StringVar(value="" if default is None else str(default))
            if widget_kind == "combobox":
                choices = [str(choice) for choice in (getattr(field, "choices", None) or [])]
                widget: tk.Widget = ttk.Combobox(
                    frame, textvariable=variable, values=choices, state="readonly", width=28
                )
            else:
                widget = ttk.Entry(frame, textvariable=variable, width=30)
            widget.grid(row=row, column=1, sticky="w", pady=3)
        if field.help:
            ttk.Label(frame, text=field.help, foreground="#666").grid(row=row, column=2, sticky="w")
        return variable

    def _add_edit_button(self, frame: ttk.LabelFrame, subject: Any, kind: str) -> None:
        """Add a button opening a rule's or a quest's source in the code editor.

        A subject declared outside the configuration directory — an engine quest, which is
        where `FirstBlood` and its siblings live — gets no button, because editing it would
        write to the engine rather than to the configuration. Saying so beats a button that
        writes somewhere the player did not choose.

        Args:
            frame: The frame to add the button to.
            subject: The rule or quest whose source is to be edited.
            kind: `"rule"` or `"quest"`.

        Returns:
            None
        """
        import inspect

        try:
            path = os.path.abspath(inspect.getfile(type(subject)))
        except (TypeError, OSError):  # pragma: no cover - a class defined in the interpreter
            return
        root = os.path.abspath(self.configuration.path)
        if os.path.commonpath([root, path]) != root:
            ttk.Label(frame, text="Declared by the engine; not editable here.").grid(
                row=0, column=3, sticky="w"
            )
            return
        ttk.Button(
            frame,
            text="Edit logic",
            command=lambda: self.open_editor(path, kind),
            width=12,
        ).grid(row=0, column=3, sticky="w", padx=(10, 0))

    def _add_new_source(self, page: ttk.Frame, kind: str) -> None:
        """Offer a way to add a rule or a quest to the configuration.

        Args:
            page: The tab to add the row to.
            kind: `"rule"` or `"quest"`.

        Returns:
            None
        """
        bar = ttk.Frame(page)
        bar.pack(fill="x", pady=(8, 0))
        ttk.Label(bar, text=f"New {kind} file:").pack(side="left")
        name = tk.StringVar()
        ttk.Entry(bar, textvariable=name, width=24).pack(side="left", padx=6)
        ttk.Button(
            bar, text="Create", command=lambda: self.create_source(name.get(), kind), width=10
        ).pack(side="left")

    def create_source(self, filename: str, kind: str) -> Optional[str]:
        """Create an empty source file for a new rule or quest, and open it to be written.

        A new file is created empty and *not* saved through the check, because an empty file
        declares no rule and the check would refuse it — which is correct behaviour and the
        wrong order of operations. The player writes the code and saves, and only then does
        the check see anything.

        Args:
            filename: The file name, with or without a `.py` ending.
            kind: `"rule"` or `"quest"`.

        Returns:
            Optional[str]: The path created and opened, or None when the name was refused or
            the configuration may not be edited.
        """
        if self.configuration.is_default:
            self.message.set(
                f"{self.configuration.name} is the default configuration and cannot be edited. "
                f"Duplicate it into a variant first."
            )
            return None
        name = filename.strip()
        stem = name[:-3] if name.endswith(".py") else name
        section = "rules" if kind == "rule" else "quests"
        root = os.path.abspath(self.configuration.path)
        path = os.path.abspath(os.path.join(root, section, f"{stem}.py"))
        if not stem.isidentifier() or os.path.commonpath([root, path]) != root:
            self.message.set(f"{filename} is not a file name a {kind} may be.")
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("")
        self.open_editor(path, kind)
        return path

    def open_editor(self, path: str, kind: str) -> CodeEditor:
        """Open a source file in the code editor.

        Args:
            path: The file to edit, inside the configuration directory being edited.
            kind: `"rule"` or `"quest"`.

        Returns:
            CodeEditor: The editor, which the form holds so it can be found and closed.
        """
        editor = CodeEditor(
            self.window,
            path,
            kind=kind,
            package=self.configuration.package,
            root=self.configuration.path,
            readonly_reason=(
                f"{self.configuration.name} is the default configuration and cannot be edited. "
                f"Duplicate it into a variant first."
                if self.configuration.is_default
                else None
            ),
            on_saved=self._source_saved,
        )
        self.editors_open.append(editor)
        return editor

    def _source_saved(self, path: str) -> None:
        """Load the configuration again now that a file in one of its sections has changed.

        A rule or quest file is not a field: saving one changes what the configuration *is*,
        so the form's copy of it is stale from that moment. Loading again is what turns "I
        saved a rule" into "my rule is in force", which is the one thing a player cannot
        otherwise tell — a file written and not composed looks exactly like a file written and
        composed, and the editor's own verdict is about the code rather than about the
        configuration.

        Anything the player has typed but not saved goes the way it goes when they pick another
        configuration from the selector, which is the same trade this form has already made.

        Args:
            path: The file that was written.

        Returns:
            None
        """
        name = self.configuration.name
        try:
            reloaded = load_configuration(name, root=self.root)
        except (OSError, ValueError) as error:
            # A file that cannot be composed refuses the load, and the refusal names the file.
            # A player who has just been told that is told which of their files it is.
            self.message.set(
                f"{os.path.basename(path)} was written but {name} will not load: {error}"
            )
            return
        self.configuration = reloaded
        self._rebuild()
        section = os.path.basename(os.path.dirname(path))
        self.message.set(
            f"{os.path.basename(path)} is part of {name}: "
            f"{len(reloaded.rules)} rules and {len(reloaded.quests)} quests are in force."
            f"{_not_in_force(reloaded, section)}"
        )

    # --- saving

    def values(self) -> Dict[str, Any]:
        """Return the rule field values the form currently shows.

        Two rules may declare a field of the same name — `royal_kind` is declared by several
        of chess's — and one flat dict can only hold one value for it. `section_values` is
        the honest reader; this one is kept because it is what the form has always exposed,
        and it reports the first declaration of each name rather than pretending to a
        certainty it does not have.

        Returns:
            Dict[str, Any]: The rule field names and what was typed into them.
        """
        merged: Dict[str, Any] = {}
        for _subject, fields, editors in self.entries_by_section.get("Rules", []):
            for name, variable in editors.items():
                merged.setdefault(name, variable)
        return self._collect(merged)

    def section_values(self, section: str) -> List[Tuple[Any, Dict[str, Any]]]:
        """Return what a section's form shows, per thing it configures.

        Args:
            section: One of `SECTIONS`.

        Returns:
            List[Tuple[Any, Dict[str, Any]]]: One (subject, values) pair per configured thing,
            in the order the section listed them. Per subject rather than one flat dict,
            because six pieces each declare a `name` and one dict would collapse them into one.
        """
        return [
            (subject, self._collect(editors))
            for subject, _fields, editors in self.entries_by_section.get(section, [])
        ]

    @staticmethod
    def _collect(editors: Dict[str, Any]) -> Dict[str, Any]:
        """Read the widgets into values, keeping booleans booleans and numbers numbers.

        Args:
            editors: The variables to read.

        Returns:
            Dict[str, Any]: One value per variable.
        """
        collected: Dict[str, Any] = {}
        for name, variable in editors.items():
            raw = variable.get()
            if isinstance(raw, bool):
                collected[name] = raw
                continue
            try:
                collected[name] = int(raw)
            except (TypeError, ValueError):
                collected[name] = raw
        return collected

    def save(self) -> bool:
        """Apply the form to the configuration, and write the values to disk.

        The default configuration refuses to be written, and says so here rather than raising:
        a player who opens settings over the game they are playing — which is chess, and
        therefore the default — must be told to duplicate it rather than shown a traceback.

        Returns:
            bool: True when the values were written. False when the configuration refused,
            which is only ever the default.
        """
        # Ask before touching anything, not after. Every section used to be applied first and
        # the guard consulted last, so a refused save had already resized the board the running
        # game is playing on and stranded half the pieces — and then said nothing had been
        # written. `Configuration.board` is the live board, so applying is not undoable by
        # declining to save.
        if self.configuration.is_default:
            self.message.set(
                f"{self.configuration.name} is the default configuration and cannot be edited. "
                f"Duplicate it into a variant first."
            )
            return False

        for section in SECTIONS:
            for subject, values in self.section_values(section):
                fields = _declared_by(subject, section)
                _apply(subject, fields, values, section)

        try:
            self.configuration.save_values()
        except PermissionError as error:
            self.message.set(str(error))
            return False

        self.close()
        if self.on_saved is not None:
            self.on_saved(self.configuration)
        return True

    def reset(self) -> None:
        """Put every field back to the value its own declaration names.

        Each subject is reset from its own declaration, so one rule's `royal_kind` returning to
        `"king"` does not silently reset another's to something else.

        Returns:
            None
        """
        for entries in self.entries_by_section.values():
            for _subject, fields, editors in entries:
                for field in fields:
                    variable = editors.get(field.name)
                    if variable is None:
                        continue
                    value = field.default
                    variable.set("" if value is None else str(value))

    def cancel(self) -> None:
        """Close without applying anything.

        Returns:
            None
        """
        for editor in list(self.editors_open):
            editor.close()
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


def _not_in_force(configuration: Configuration, section: Optional[str] = None) -> str:
    """Return what the form says about the files in a section that join nothing.

    A file in a composed section that declares no entry contributes nothing, which is what a
    helper module is for and what a file the player has not finished looks like. Nothing
    about the two is distinguishable from the form, so each is named rather than one of them
    being quietly kept.

    Args:
        configuration: The configuration just loaded.
        section: The section directory to report on, for instance `rules`. Defaults to None,
            which reports every section.

    Returns:
        str: One clause naming each file and saying it is not in force, prefixed by "Not in
        force:", or "" when every file in the section is in force. Paths are relative to the
        configuration directory, which is where a player looks for the file.
    """
    prefix = os.path.join(configuration.path, section or "", "")
    reported = [
        note[len(configuration.path) + len(os.sep) :]
        for note in configuration.uncomposed
        if note.startswith(prefix)
    ]
    if not reported:
        return ""
    return " Not in force: " + "; ".join(reported)


def _apply(subject: Any, fields: List[Field], values: Dict[str, Any], section: str) -> None:
    """Write a form's values onto the thing they configure.

    Each kind of configurable writes to a different place, and the difference is the point: a
    rule's values are its configured `value` dict so they can be persisted, a quest's are its
    attributes, a board's change its dimensions, and a clock's go through the clock helper
    that knows a clock keeps its initial time in two places.

    Args:
        subject: The rule, quest, board, piece or clock being configured.
        fields: What it declared.
        values: What the player chose.
        section: Which section this is, which decides where the values are written.

    Returns:
        None
    """
    chosen = {field.name: values[field.name] for field in fields if field.name in values}
    if not chosen:
        return
    if section == "Clocks":
        apply_clock_values(subject, chosen)
        return
    if section == "Board":
        # The board a configuration holds is the board a running game plays on — there is no
        # second board until `new_game` deals one — so resizing it here ends the game in
        # progress. The form says so, and the change takes hold for the next game.
        subject.set_dimensions(
            int(chosen.get("rows", subject.rows)), int(chosen.get("cols", subject.cols))
        )
        return
    if section == "Rules":
        # `enabled` is a rule's own switch, not a configured value, so it goes to the
        # attribute; everything else is the rule's configured `value`, which is what gets
        # persisted and what the form is editing.
        if "enabled" in chosen:
            subject.enabled = bool(chosen.pop("enabled"))
        subject.value.update(chosen)
        return
    if section == "Pieces":
        # A piece's declaration is richer than its attributes — two symbols in one tuple,
        # vectors shown as text — so the piece applies its own values rather than the form
        # setting attributes the declaration never named. The subject is the class, so it is
        # built once here: every piece the game places afterwards carries what was typed.
        subject(1).apply_values(chosen)
        return
    for name, value in chosen.items():
        setattr(subject, name, value)


def _declared_by(subject: Any, section: str) -> List[Field]:
    """Return the declaration the values in a section's form were read against.

    Args:
        subject: The thing being configured.
        section: Which section it is in, which decides which declaration is asked for.

    Returns:
        List[Field]: The declaration, or the subject's own when there is none — a board's and
        a clock's are asked for directly rather than through the rule or quest pattern.
    """
    if section == "Board":
        return subject.value_fields()
    if section == "Clocks":
        return clock_fields(subject)
    if section == "Rules":
        return _rule_parameters(subject)
    return _safe_fields(subject)


def _rule_parameters(rule: Any) -> List[Field]:
    """Return everything a rule is configurable with, `enabled` included.

    Args:
        rule: The rule to describe.

    Returns:
        List[Field]: The rule's own declaration with the framework's `enabled` in front of it,
        or just `enabled` for a rule that declares nothing.
    """
    enabled = Field("enabled", "boolean", "In force", bool(getattr(rule, "enabled", True)))
    return [enabled, *_safe_fields(rule)]


def _safe_fields(subject: Any) -> List[Field]:
    """Return what a subject declares, or nothing if it cannot say.

    Args:
        subject: The rule or quest to ask.

    Returns:
        List[Field]: Its declaration, or an empty list if it declares nothing or raises. A rule
        that cannot describe itself is still configurable by whatever it declares later.
    """
    target = subject
    if isinstance(target, type):
        # A piece is configured through its *class* — that is what the configuration holds, and
        # what the values are saved against. Asking the class itself for its declaration is an
        # unbound call missing its `self`, so one instance is built to ask on its behalf.
        probe = _probe(target)
        if probe is None:
            return []
        target = probe
    try:
        fields = target.value_fields()
    except Exception:  # noqa: BLE001 - a rule may not declare fields at all
        try:
            fields = target.parameters()
        except Exception:  # noqa: BLE001 - nor may it declare parameters
            fields = []
    return fields if isinstance(fields, list) else []


def _probe(piece_class: type) -> Any:
    """Return one instance of a piece class, so its declaration can be read.

    A piece is always built for a colour, so a colour is tried. White first, and Black if
    White will not do — a piece class that refuses both is described by name alone in the
    form, because there is no instance of it to describe. What is being read is the class's
    *declaration*, which does not vary by colour: the white and black symbols are both in it.

    Args:
        piece_class: The piece class the configuration offers.

    Returns:
        Any: An instance for a class that can be built, or None for one that cannot.
    """
    for colour in (1, -1):
        try:
            return piece_class(colour)
        except Exception:  # noqa: BLE001 - any failure means there is no instance to describe
            continue
    return None


def _unused_name(source: str, taken: List[str]) -> str:
    """Return a configuration name derived from another that nothing is using.

    Args:
        source: The name to derive from.
        taken: The names already in use.

    Returns:
        str: A name like `chess_copy`, or `chess_copy_2`, that is not in `taken`.
    """
    candidate = f"{source}_copy"
    index = 2
    while candidate in taken:
        candidate = f"{source}_copy_{index}"
        index += 1
    return candidate


def _ask(master: tk.Misc, title: str, prompt: str, initial: str) -> Optional[str]:
    """Ask for a line of text.

    Args:
        master: The window the prompt belongs to.
        title: The prompt window's title.
        prompt: The question to ask.
        initial: What the field starts with.

    Returns:
        Optional[str]: What was typed, or None when the prompt was cancelled or dismissed.
    """
    from tkinter import simpledialog

    return simpledialog.askstring(title, prompt, initialvalue=initial, parent=master)


# Re-exported so a caller wiring the form does not have to know which module declares what.
__all__ = ["Configuration", "SettingsDialog", "SECTIONS", "editable_sources"]
