"""Loading a configuration.

A configuration is a directory under `games/`, and it is composed out loud: the sections it
has are declared by `CONFIGURATION_SECTIONS`, and each one composes the modules its own
directory holds. There is no registry, no plugin loader and no scan of anything else, so what
a configuration is made of is what its directory holds — and a copy composes the copy's files
rather than the original's, which is the failure `games/chess/__init__.py` exists to prevent.

Loading is bounded on purpose. Code loads from inside the configuration directory being
edited and from nowhere else — never an arbitrary path, never an environment variable —
because the product runs the Python a player writes.
"""

import importlib.util
import json
import os
import re
import shutil
import sys
from types import ModuleType
from typing import Callable, Any, Dict, FrozenSet, Iterable, List, Optional

from model.game.board import Board
from model.game.clock import Clock
from model.game.games import DEFAULT_GAME, available_games, games_root
from model.game.quest import Quest
from model.game.rule import Rule
from model.misc.export_writers import ExportWriter
from model.pieces.piece import Piece

#: The sections a configuration directory holds, and what each one composes. Every section names
#: the parent class its modules must derive from, and is composed out of the files in its own
#: directory: one entry per subclass that class declares is in force — the class itself for a
#: section in `CLASS_ENTRY_SECTIONS`, an instance built from it otherwise. There is no section
#: left `None`, because `None` was how `pieces/`, `clocks/` and `export/` said "composed by hand"
#: while a file a player wrote into one of them joined nothing — and a hand-written list beside a
#: directory is exactly the defect composition removes.
CONFIGURATION_SECTIONS: Dict[str, Optional[type]] = {
    "pieces": Piece,
    "rules": Rule,
    "quests": Quest,
    "clocks": Clock,
    "export": ExportWriter,
}

#: The sections whose composed entry is the declared class itself rather than an instance built
#: from it. `Configuration.pieces` is a catalogue of what a board may hold, and a piece is placed
#: by the board with a colour and a square: `Piece` cannot be built with no arguments at all,
#: because a piece has no colour until it is placed. Everything else in a section is one object the
#: game holds for the whole of it — a rule, a quest, a clock, a writer — so those are instances.
CLASS_ENTRY_SECTIONS: FrozenSet[str] = frozenset({"pieces"})


#: The file a Python package is itself in. A section holds it like any other file, and it is
#: the one file in a section that is already imported.
_PACKAGE_MODULE = "__init__.py"


class ConfigurationSourceError(ValueError):
    """A file in a configuration's section could not be composed into the configuration.

    Raised by `compose_section`, always with a message naming the file and what is wrong
    with it. It is a `ValueError` because every caller that loads a configuration already
    handles one — `view/settings_dialog.py` puts the message in the form rather than showing a
    traceback to a player — and because a section holding a file that cannot be read is a
    problem with what was loaded rather than with the loader.
    """


class Configuration:
    """One game, assembled: a board, its pieces, its rules, its quests and its clocks.

    Attributes:
        name: The configuration's directory name.
        path: Absolute path to the configuration directory.
        board: The board the game runs on.
        pieces: The piece classes this configuration offers, composed out of `pieces/`.
        rules: The rules in force, in the order `compose_section` composes them: the
            section's own module first, then the rest of its files by name.
        quests: The quests available, composed out of `quests/`.
        clocks: The clock configurations available, composed out of `clocks/`.
        exporters: The export writers this configuration offers, composed out of `export/`.
            Every writer the section holds is here whatever order `export/` prefers them in;
            the preference decides only which of them leads.
        notation: How this configuration names its squares and its moves, for the window to
            draw them with. It is whatever answers `move_label(number, move)`, and it is
            optional: a configuration that names its squares in no notation gets its move
            history as coordinate pairs. The engine holds no naming of its own, so there is
            nothing here to be right or wrong about.
        metadata: The record of who played, when and how the game ended, handed to the
            writers that need one. It is optional, and the engine reads it without knowing
            what it is: which tags a written game carries is the same question as which
            notations it can be written in, and the answer to that is a configuration's. A
            configuration that declares none gets `None` rather than a record the engine
            made up, because a record of a game nobody described is a record of nothing.
        uncomposed: One line per file in a composed section that contributes nothing to the
            configuration, each naming the file and saying why. A section legitimately holds
            helpers beside its entries, so a file that declares no entry is not an error —
            but a file the player wrote and did not finish looks exactly like a helper, and
            without this the two are indistinguishable from the settings form.
        package: The module name the configuration is registered under, so a module inside it
            can resolve its relative imports. Empty until the configuration is loaded from a
            directory, which is the only way a relative import can work at all.
    """

    def __init__(
        self,
        name: str,
        path: str,
        board: Optional[Board] = None,
        pieces: Optional[Iterable[type]] = None,
        rules: Optional[Iterable[Rule]] = None,
        quests: Optional[Iterable[Quest]] = None,
        clocks: Optional[Iterable[Any]] = None,
        exporters: Optional[Iterable[Any]] = None,
        notation: Optional[Any] = None,
        metadata: Optional[Any] = None,
        board_factory: Optional[Callable[[], Board]] = None,
        uncomposed: Optional[Iterable[str]] = None,
    ):
        """Assemble a configuration.

        Args:
            name: The configuration's directory name.
            path: Absolute path to the configuration directory.
            board: The board the game runs on.
            pieces: The piece classes this configuration offers, composed out of `pieces/`.
            rules: The rules in force, in the order the configuration's own rules section
                composed them.
            quests: The quests available, composed out of `quests/`.
            clocks: The clock configurations available, composed out of `clocks/`.
            exporters: The export writers this configuration offers, composed out of
                `export/`. Every writer that section declares is included; the section's own
                declared order decides which of them leads.
            notation: How this configuration names a move, for the window to draw the move
                history with. Anything answering `move_label(number, move)` will do; None
                means the game is drawn with coordinates.
            metadata: The record of the game's facts a writer needs in order to write a game
                up, handed to the writers that ask for one. Anything will do; None means this
                configuration describes none, and the engine writes no header of its own.
            board_factory: Builds a fresh board for this configuration. Holding one board
                means one game; holding the way to build one means as many games as the
                player has time for.
            uncomposed: One line per file in any composed section that contributes nothing,
                each naming the file and saying why. Collected by `compose_section` through
                the list passed to it by the configuration's own `build_…()` functions for
                every section it composes.
        """
        self.name = name
        self.path = path
        self.board = board
        self.pieces: List[type] = list(pieces) if pieces else []
        self.rules: List[Rule] = list(rules) if rules else []
        self.quests: List[Quest] = list(quests) if quests else []
        self.clocks: List[Any] = list(clocks) if clocks else []
        self.exporters: List[Any] = list(exporters) if exporters else []
        self.notation: Optional[Any] = notation
        self.metadata: Optional[Any] = metadata
        self.board_factory: Optional[Callable[[], Board]] = board_factory
        self.uncomposed: List[str] = list(uncomposed) if uncomposed else []
        self.package: str = ""

    @property
    def is_default(self) -> bool:
        """Whether this is the shipped default configuration, which may not be edited.

        The default configuration is the one a game runs when the player selects nothing, so
        it is the reference every variant is compared against. A variant starts by duplicating
        it, and the default itself is left exactly as shipped — which is only a rule if
        something enforces it, because `save_values` can write into its directory perfectly
        well.

        Returns:
            bool: True for the configuration named by `DEFAULT_GAME`.
        """
        return self.name == DEFAULT_GAME

    def new_board(self) -> Board:
        """Build a fresh board for a new game of this configuration.

        Returns:
            Board: A newly dealt board. A configuration that declared no factory gets the
            board it already holds, so `new_game` always returns a playable board even when
            a configuration declares only one.
        """
        if self.board_factory is not None:
            return self.board_factory()
        if self.board is not None:
            return self.board
        return Board()

    def enabled_rules(self) -> List[Rule]:
        """Return the rules that are in force, in declaration order.

        Returns:
            List[Rule]: The rules whose `enabled` is True.
        """
        return [rule for rule in self.rules if rule.enabled]

    def reset(self) -> None:
        """Clear every rule's runtime state for a new game.

        Returns:
            None
        """
        for rule in self.rules:
            rule.reset()

    def values(self) -> Dict[str, Any]:
        """Return everything about this configuration that may be written to disk.

        Returns:
            Dict[str, Any]: The name, the board dimensions and every rule's and quest's
            configured values. No rule's runtime state is here, so saving a configuration
            cannot save a game's history.
        """
        return {
            "name": self.name,
            "board": list(self.board.dimensions) if self.board is not None else None,
            "rules": {rule.label: rule.persisted_values() for rule in self.rules},
            "quests": {
                quest.name: {"reward": quest.reward, "enabled": quest.enabled}
                for quest in self.quests
            },
        }

    def save_values(self, path: Optional[str] = None) -> str:
        """Write the configurable values to disk as JSON.

        Only values are written. Runtime state is not part of `values()`, so it cannot
        reach the file even by accident.

        The default configuration is not written to. It is the reference a variant is
        duplicated from, so editing it in place destroys the one thing every variant is
        compared against, and no warning is given. Writing it *outside* its own directory
        is fine: that is an export, not an edit.

        Args:
            path: Where to write. Defaults to `<configuration path>/configuration.json`.

        Returns:
            str: The path written.

        Raises:
            PermissionError: If the target is inside the default configuration's directory.
        """
        target = path or os.path.join(self.path, "configuration.json")
        if self.is_default and _within(os.path.abspath(target), os.path.abspath(self.path)):
            raise PermissionError(
                f"{self.name} is the default configuration and cannot be edited; "
                f"duplicate it into a variant and edit that instead"
            )
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(self.values(), handle, indent=2, sort_keys=True, default=str)
        return target

    def __repr__(self) -> str:
        """Return a debugging representation naming the configuration.

        Returns:
            str: The name, its path, and how many rules and quests it holds.
        """
        return (
            f"Configuration(name={self.name!r}, path={self.path!r}, "
            f"rules={len(self.rules)}, quests={len(self.quests)})"
        )


def compose_section(
    section: ModuleType,
    notes: Optional[List[str]] = None,
    preferred: Iterable[Optional[type]] = (),
) -> List[Any]:
    """Compose the entries every module in one configuration section declares.

    A section is a directory of a configuration, and the modules in it are what the
    configuration has: `pieces/zz_new.py` is in the catalogue because it is a file in `pieces/`,
    with no list anywhere to add its name to. This is the whole of the composition, and it is
    deliberately the only one. `CONFIGURATION_SECTIONS` says what a module in the section must
    derive from, and this walks the files the section holds — no registry, no plugin loader, and
    nothing outside the section's own directory.

    Composition is over the section's own package rather than over a path and a module name,
    because a configuration can be copied. `games/chess/__init__.py` exists to keep a copy
    loading its own files, and a composition that looked the section up by name would undo
    that: the copy would compose `games.chess.rules` and play the original's rules while
    looking as though it had loaded its own.

    **Order** is the section package first — `__init__.py` is a real file in the section and
    may declare entries of its own — and then the remaining modules by file name. A directory
    listing is in whatever order the filesystem hands back, and rule order is the tie-break
    when two rules propose an outcome at once: `resolve_outcomes` takes the first of two
    equally strong proposals. Sorted file names are the one order a player can predict,
    reproduce by hand and read off the settings form.

    **`preferred` is an ordering, never a membership.** A section may declare which of its
    entries lead — `export/` does, because `GameManager.default_format` takes the first format
    the first writer declares and `save_log` names its file from it, which is a preference
    rather than a fact about the directory. Everything the directory declares is composed and
    returned whatever the preference says; a name in `preferred` that nothing declares is a
    refusal rather than a shrug, because a preference for a writer that is not there is exactly
    the way the directory and the declaration drift apart unnoticed.

    **A file that cannot be imported refuses the load.** The alternative is a game that plays
    without a file the player put there and says nothing at all, which is the failure this
    replaces. **A file that declares nothing usable is left out**, because a section
    legitimately holds helpers beside its entries — `games/chess/rules/attacks.py` holds the
    ray and attack geometry three rule files share — and a half-written file must not stop
    the game starting. Either way the file is named: in the message of a refusal, and in
    `notes` for a file left out, which the settings form shows.

    Args:
        section: The section's package, already imported. A section's own `__init__.py`
            passes `sys.modules[__name__]`, so what is composed is the copy's section and not
            the original's.
        notes: A list to append one line to per file that contributes nothing. Defaults to
            None, which discards them.
        preferred: The classes to place first, in the order given. Entries whose class is not
            named follow, in composed order, and nothing is dropped for not being named.
            Defaults to an empty sequence, which is the composed order unchanged.

    Returns:
        List[Any]: One entry per class the section's modules declare — the class itself for a
            section in `CLASS_ENTRY_SECTIONS`, otherwise one instance built from it — in the
        order described above. Empty for a section that declares nothing, which is a
        configuration that offers no rule of that kind rather than a failure.

    Raises:
        ConfigurationSourceError: If `section` is not a declared section or is declared with
            no parent class, if a file in it cannot be imported, if a class it declares cannot
            be built, or if `preferred` names a class the section does not declare.
    """
    directory = _section_directory(section)
    name = os.path.basename(directory)
    base = CONFIGURATION_SECTIONS.get(name)
    if base is None:
        raise ConfigurationSourceError(
            f"{section.__name__} is not one of the declared sections: "
            f"{', '.join(sorted(CONFIGURATION_SECTIONS))}. Only a section whose parent class "
            f"is declared is composed out of the modules in its directory, and every "
            f"declared section names one."
        )
    # A file written since this process last looked is invisible to the finder until the
    # caches are dropped, and writing one is exactly how a rule reaches a configuration: the
    # editor saves the file and the configuration is loaded again in the same process.
    importlib.invalidate_caches()

    entries: List[Any] = []
    composed_of: List[Optional[type]] = []
    for filename in _section_files(directory):
        path = os.path.join(directory, filename)
        module = _section_module(section, filename, path)
        declared = _declared_entries(module, base)
        if not declared:
            # The section's own module is where the composition lives, so a section that
            # declares no entry of its own is the ordinary case and is not worth reporting.
            if notes is not None and filename != _PACKAGE_MODULE:
                notes.append(f"{path} declares no {base.__name__}")
            continue
        built = _build_entries(declared, path, name)
        entries.extend(built)
        composed_of.extend(declared)
    return _ordered_by_preference(entries, composed_of, preferred, name)


def _ordered_by_preference(
    entries: List[Any],
    composed_of: List[Optional[type]],
    preferred: Iterable[Optional[type]],
    name: str,
) -> List[Any]:
    """Return the composed entries with the preferred classes first, and nothing dropped.

    Args:
        entries: The composed entries, in composed order.
        composed_of: The class each entry was composed from, in the same order.
        preferred: The classes to place first, in the order given.
        name: The section's directory name, used in the message of a refusal.

    Returns:
        List[Any]: The same entries, reordered. Every entry is present exactly once.

    Raises:
        ConfigurationSourceError: If `preferred` names a class the section did not compose,
            naming the class and the section.
    """
    ranks = {cls: rank for rank, cls in enumerate(preferred)}
    if not ranks:
        return entries
    absent = [cls for cls in ranks if cls not in composed_of]
    if absent:
        named = ", ".join(getattr(cls, "__name__", repr(cls)) for cls in absent)
        raise ConfigurationSourceError(
            f"the {name} section prefers {named}, which its files do not declare, so this "
            f"configuration will not load: the preference and the directory have drifted apart"
        )
    # A stable sort, so an entry the preference does not name keeps its composed order and
    # follows everything the preference does name, and a file that declares nothing is still
    # composed rather than dropped for not being listed.
    ordered = sorted(zip(entries, composed_of), key=lambda pair: ranks.get(pair[1], len(ranks)))
    return [entry for entry, _declared in ordered]


def _section_directory(section: ModuleType) -> str:
    """Return the directory one configuration section holds its modules in.

    Args:
        section: The section's package.

    Returns:
        str: The section's own directory, which is the first entry of its search path.

    Raises:
        ConfigurationSourceError: If `section` has no search path, which means it is not a
            package and so has no directory of modules to compose.
    """
    paths = list(getattr(section, "__path__", None) or [])
    if not paths:
        raise ConfigurationSourceError(
            f"{getattr(section, '__name__', section)} is not a package, so it has no "
            f"directory of modules to compose; a section is a directory of a configuration"
        )
    return paths[0]


def _section_files(directory: str) -> List[str]:
    """Return the module files a section holds, in the order they are composed.

    Args:
        directory: The section's own directory.

    Returns:
        List[str]: Every `.py` file name in the directory, the section's own module first
        and the rest sorted by name. The package leads because it is composed first, not
        because an underscore happens to sort early.
    """
    names = sorted(name for name in os.listdir(directory) if name.endswith(".py"))
    if _PACKAGE_MODULE in names:
        names.remove(_PACKAGE_MODULE)
        names.insert(0, _PACKAGE_MODULE)
    return names


def _section_module(section: ModuleType, filename: str, path: str) -> ModuleType:
    """Return one module of a section, importing it against the section's own package.

    Args:
        section: The section's package.
        filename: The file's name, ending in `.py`.
        path: The file's path, used in the message of a failure.

    Returns:
        ModuleType: The module. The section's own module is returned rather than imported a
        second time, because it is already imported — it is the package doing the composing.

    Raises:
        ConfigurationSourceError: If the file cannot be imported, naming the file and the
            exception it raised.
    """
    if filename == _PACKAGE_MODULE:
        return section
    try:
        return importlib.import_module(f".{filename[: -len('.py')]}", package=section.__name__)
    except Exception as error:  # noqa: BLE001 - every failure here is the player's code
        raise ConfigurationSourceError(
            f"{path} could not be imported, so this configuration will not load: "
            f"{type(error).__name__}: {error}"
        ) from error


def _declared_entries(module: ModuleType, base: type) -> List[type]:
    """Return the classes one module of a section declares for the section to compose.

    A class the module merely imported is not one it declares, and is left to the module that
    does declare it: `castling.py` importing `attacks.py`'s helpers must not compose them,
    and a rule shared between two files must not be in force twice.

    Args:
        module: The module to read.
        base: The parent class an entry of the section derives from.

    Returns:
        List[type]: The declared classes, in the order the module declares them.
    """
    declared = [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and value is not base
        and issubclass(value, base)
        and value.__module__ == module.__name__
    ]
    return list(dict.fromkeys(declared))


def _build_entries(declared: List[type], path: str, name: str) -> List[Any]:
    """Build one entry from each class a section's module declares.

    An entry a section composes is built with no arguments, because the section is what knows
    what it holds and it has only the class to go on. A class that insists on an argument
    cannot be composed that way, and is said so rather than left to fail at game start.

    **One section is exempt**: `CLASS_ENTRY_SECTIONS` names `pieces`, whose entry is the class
    itself. A board places a piece by building one with a colour and a square, and a piece with
    no colour is not a piece — so a catalogue of *classes* is what a piece section composes, and
    asking for instances would refuse every piece in the tree.

    Args:
        declared: The classes the module declares.
        path: The file they were declared in, used in the message of a failure.
        name: The section's directory name, used to say whether this section composes classes.

    Returns:
        List[Any]: One entry per class — the class itself for a class-entry section, otherwise
        one instance built from it.

    Raises:
        ConfigurationSourceError: If a class cannot be built, naming the file, the class and
            the exception it raised.
    """
    if name in CLASS_ENTRY_SECTIONS:
        return list(declared)
    built: List[Any] = []
    for candidate in declared:
        try:
            built.append(candidate())
        except Exception as error:  # noqa: BLE001 - any failure here is the player's code
            raise ConfigurationSourceError(
                f"{path}: {candidate.__name__} could not be built, so this configuration "
                f"will not load: {type(error).__name__}: {error}"
            ) from error
    return built


def _within(candidate: str, directory: str) -> bool:
    """Report whether a path lies inside a directory.

    Args:
        candidate: The path to test. Must already be absolute.
        directory: The containing directory. Must already be absolute.

    Returns:
        bool: True when `candidate` is inside `directory` or is `directory` itself.
    """
    try:
        return os.path.commonpath([candidate, directory]) == directory
    except ValueError:  # pragma: no cover - different drives on Windows
        return False


def _validate_name(name: str) -> str:
    """Check that a name may be used for a configuration directory.

    A name becomes both a directory and the module name a loaded configuration is registered
    under, so it has to be one path segment and an identifier. Anything else is either a
    traversal or a name Python will not accept.

    Args:
        name: The proposed directory name.

    Returns:
        str: The name, unchanged.

    Raises:
        ValueError: If the name is empty, holds a path separator, or is a relative marker.
    """
    if not name or os.path.sep in name or name in (".", "..") or not name.isidentifier():
        raise ValueError(f"{name!r} is not a configuration name")
    return name


def copy_configuration(source: str, name: str, root: Optional[str] = None) -> Configuration:
    """Duplicate a configuration directory into a new variant, and load the copy.

    Duplication is the extension mechanism: `SCRATCHPAD.md` section 2 makes copying a
    directory how a variant comes into existence, so this is that move with the loading
    done and the copy refused where it would be wrong.

    Args:
        source: The configuration directory name to copy from.
        name: The variant's directory name.
        root: The directory configurations must live under. Defaults to the shipped `games/`.

    Returns:
        Configuration: The loaded copy, which is a variant in its own right.

    Raises:
        ValueError: If `name` is not a usable configuration name.
        FileNotFoundError: If there is no configuration named `source`.
        FileExistsError: If `name` already exists, so nothing is overwritten.
    """
    _validate_name(name)
    if name == DEFAULT_GAME:
        raise ValueError(f"{DEFAULT_GAME} is the default configuration and already exists")
    allowed = os.path.abspath(root or games_root())
    origin = os.path.join(allowed, source)
    if not os.path.isdir(origin):
        raise FileNotFoundError(f"no configuration directory named {source!r} in {allowed}")
    target = os.path.join(allowed, name)
    if os.path.exists(target):
        raise FileExistsError(f"{target} already exists")
    shutil.copytree(origin, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return load_configuration_at(target, root=allowed)


def rename_configuration(name: str, new_name: str, root: Optional[str] = None) -> Configuration:
    """Rename a configuration directory, and load it under its new name.

    Args:
        name: The configuration directory's current name.
        new_name: The name to give it.
        root: The directory configurations must live under. Defaults to the shipped `games/`.

    Returns:
        Configuration: The loaded configuration under its new name.

    Raises:
        ValueError: If `new_name` is not usable, or names the configuration being renamed.
        FileNotFoundError: If there is no configuration named `name`.
        FileExistsError: If `new_name` is already taken.
    """
    # Both names become path segments. Validating only the new one left `name` free to be "..",
    # which renamed the directory *containing* `games/` out from under the caller.
    _validate_name(name)
    _validate_name(new_name)
    if new_name == DEFAULT_GAME:
        raise ValueError(f"{DEFAULT_GAME} is the default configuration and cannot take a name")
    allowed = os.path.abspath(root or games_root())
    origin = os.path.join(allowed, name)
    if not os.path.isdir(origin):
        raise FileNotFoundError(f"no configuration directory named {name!r} in {allowed}")
    if name == DEFAULT_GAME:
        raise PermissionError(f"{DEFAULT_GAME} is the default configuration and cannot be renamed")
    if new_name == name:
        return load_configuration(name, root=allowed)
    target = os.path.join(allowed, new_name)
    if os.path.exists(target):
        raise FileExistsError(f"{target} already exists")
    os.rename(origin, target)
    return load_configuration_at(target, root=allowed)


def delete_configuration(name: str, root: Optional[str] = None) -> None:
    """Delete a configuration directory.

    Args:
        name: The configuration directory to remove.
        root: The directory configurations must live under. Defaults to the shipped `games/`.

    Returns:
        None

    Raises:
        PermissionError: If asked to delete the default configuration.
        FileNotFoundError: If there is no configuration named `name`.
    """
    allowed = os.path.abspath(root or games_root())
    # Without this, `name=".."` resolved to the directory *containing* `games/` and
    # `shutil.rmtree` removed everything above it: the function was handed a name and used
    # it as a path without ever asking whether it was one path segment.
    _validate_name(name)
    if name == DEFAULT_GAME:
        raise PermissionError(f"{DEFAULT_GAME} is the default configuration and cannot be deleted")
    target = os.path.join(allowed, name)
    if not os.path.isdir(target):
        raise FileNotFoundError(f"no configuration directory named {name!r} in {allowed}")
    shutil.rmtree(target)


def load_configuration_at(path: str, root: Optional[str] = None) -> Configuration:
    """Load a configuration from a directory path.

    Args:
        path: Absolute path to the configuration directory.
        root: The directory configurations must live under. Defaults to the shipped
            `games/` directory.

    Returns:
        Configuration: The assembled configuration.

    Raises:
        ValueError: If `path` is not inside `root`. Loading player-authored code from an
            arbitrary path is exactly what the bound is for.
        ConfigurationSourceError: If a file in one of the configuration's composed sections
            cannot be composed. The message names the file, and refusing is the point: a
            configuration that loaded without one of its files would play a game the player
            does not believe they are playing.
        FileNotFoundError: If `path` is not a directory, or holds no `build_configuration`.
    """
    allowed = os.path.abspath(root or games_root())
    resolved = os.path.abspath(path)
    if os.path.commonpath([allowed, resolved]) != allowed:
        raise ValueError(f"a configuration must live under {allowed}; {resolved} is outside it")
    if not os.path.isdir(resolved):
        raise FileNotFoundError(f"no configuration directory at {resolved}")

    name = os.path.basename(resolved)
    entry_point = os.path.join(resolved, "__init__.py")
    if not os.path.isfile(entry_point):
        raise FileNotFoundError(f"{resolved} holds no __init__.py, so it is not a configuration")

    module = _import_from_path(entry_point, resolved)
    builder = getattr(module, "build_configuration", None)
    if builder is None:
        raise FileNotFoundError(f"{resolved} declares no build_configuration()")

    try:
        configuration = builder()
    except Exception:
        # A file in a section that cannot be composed is a failure a player hits and fixes,
        # so the half-built package must not stay in `sys.modules` under this directory's
        # name while they do: the next attempt would find the modules already loaded and
        # compose from a mixture of two loads.
        _purge_module(module.__name__)
        raise
    configuration.name = name
    configuration.path = resolved
    configuration.package = module.__name__
    return configuration


def _purge_module(module_name: str) -> None:
    """Forget a module and everything loaded beneath it.

    Args:
        module_name: The module to remove from `sys.modules`.

    Returns:
        None
    """
    prefix = module_name + "."
    for cached in [name for name in sys.modules if name == module_name or name.startswith(prefix)]:
        sys.modules.pop(cached, None)


def _import_from_path(entry_point: str, directory: str) -> Any:
    """Import a configuration's `__init__.py` as a package rooted where it lives.

    Loading by file location rather than by package name is what lets a player create a
    variant called whatever they like: the name is a directory, not an identifier the
    engine has to agree with.

    The module is registered as a *package* — its spec carries the configuration directory
    as its search path — because that is what makes `from .board import build_board` resolve
    against the copy that wrote it. Without the search path a relative import fails outright,
    and the tempting repair is an absolute `from games.chess.board import …`, which loads the
    original configuration while the copy looks like it loaded its own. So a variant gets its
    own modules here, and nothing in it needs to know what the original is called.

    Args:
        entry_point: Absolute path to the configuration's `__init__.py`.
        directory: The configuration directory, used to give the module a stable unique name.

    Returns:
        Any: The imported module.

    Raises:
        ImportError: If the module cannot be loaded.
    """
    module_name = "_configuration_" + re.sub(r"\W", "_", os.path.abspath(directory))
    spec = importlib.util.spec_from_file_location(
        module_name, entry_point, submodule_search_locations=[directory]
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load a configuration from {entry_point}")
    module = importlib.util.module_from_spec(spec)
    # Purge the previous load of this configuration, submodules included. Registering the
    # package again is not enough: a stale submodule from an earlier load stays in
    # sys.modules, so `from .rules.capture import CaptureRule` returns the cached module and
    # the same class object. The code editor then saved a rule, reported "No problems found",
    # and every reload in that process — including the running game — kept the old rule. Only a
    # fresh interpreter ever saw the edit.
    _purge_module(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        _purge_module(module_name)
        raise
    importlib.invalidate_caches()
    return module


def load_configuration(name: str, root: Optional[str] = None) -> Configuration:
    """Load a shipped configuration by name.

    Args:
        name: The configuration directory name, for example `chess`.
        root: The directory configurations must live under. Defaults to the shipped
            `games/` directory.

    Returns:
        Configuration: The assembled configuration.

    Raises:
        ValueError: If `name` is empty or names something outside the directory.
        FileNotFoundError: If no such configuration is shipped.
    """
    _validate_name(name)
    allowed = os.path.abspath(root or games_root())
    return load_configuration_at(os.path.join(allowed, name), root=allowed)


def load_default_configuration(root: Optional[str] = None) -> Configuration:
    """Load the configuration a game runs when the player selects nothing.

    Args:
        root: The directory configurations must live under. Defaults to the shipped
            `games/` directory.

    Returns:
        Configuration: The assembled configuration.

    Raises:
        FileNotFoundError: If no configuration is shipped at all.
    """
    shipped = available_games()
    if not shipped:
        raise FileNotFoundError(f"no configurations are shipped in {root or games_root()}")
    return load_configuration(shipped[0], root=root)
