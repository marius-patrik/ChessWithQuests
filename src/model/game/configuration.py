"""Loading a configuration.

A configuration is a directory under `games/`, and it is composed explicitly: the
configuration's own module says what it is made of. There is no registry and no
discovery-by-name, so the set of rules in force is closed, greppable and known at the point
of use.

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
from typing import Callable, Any, Dict, Iterable, List, Optional

from model.game.board import Board
from model.game.games import DEFAULT_GAME, available_games, games_root
from model.game.quest import Quest
from model.game.rule import Rule

#: Subdirectories a configuration directory holds.
CONFIGURATION_SECTIONS = ("pieces", "rules", "quests", "clocks", "export")


class Configuration:
    """One game, assembled: a board, its pieces, its rules, its quests and its clocks.

    Attributes:
        name: The configuration's directory name.
        path: Absolute path to the configuration directory.
        board: The board the game runs on.
        pieces: The piece classes this configuration offers.
        rules: The rules in force, in the order they are declared.
        quests: The quests available.
        clocks: The clock configurations available.
        exporters: The export writers this configuration offers.
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
        board_factory: Optional[Callable[[], Board]] = None,
    ):
        """Assemble a configuration.

        Args:
            name: The configuration's directory name.
            path: Absolute path to the configuration directory.
            board: The board the game runs on.
            pieces: The piece classes this configuration offers.
            rules: The rules in force, in the order they are declared.
            quests: The quests available.
            clocks: The clock configurations available.
            exporters: The export writers this configuration offers.
            board_factory: Builds a fresh board for this configuration. Holding one board
                means one game; holding the way to build one means as many games as the
                player has time for.
        """
        self.name = name
        self.path = path
        self.board = board
        self.pieces: List[type] = list(pieces) if pieces else []
        self.rules: List[Rule] = list(rules) if rules else []
        self.quests: List[Quest] = list(quests) if quests else []
        self.clocks: List[Any] = list(clocks) if clocks else []
        self.exporters: List[Any] = list(exporters) if exporters else []
        self.board_factory: Optional[Callable[[], Board]] = board_factory

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

    configuration = builder()
    configuration.name = name
    configuration.path = resolved
    return configuration


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
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
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
