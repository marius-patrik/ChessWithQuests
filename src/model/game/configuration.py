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
import sys
from typing import Any, Dict, Iterable, List, Optional

from model.game.board import Board
from model.game.games import available_games, games_root
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
        """
        self.name = name
        self.path = path
        self.board = board
        self.pieces: List[type] = list(pieces) if pieces else []
        self.rules: List[Rule] = list(rules) if rules else []
        self.quests: List[Quest] = list(quests) if quests else []
        self.clocks: List[Any] = list(clocks) if clocks else []
        self.exporters: List[Any] = list(exporters) if exporters else []

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

        Args:
            path: Where to write. Defaults to `<configuration path>/configuration.json`.

        Returns:
            str: The path written.
        """
        target = path or os.path.join(self.path, "configuration.json")
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
    """Import a configuration's `__init__.py` from where it lives.

    Loading by file location rather than by package name is what lets a player create a
    variant called whatever they like: the name is a directory, not an identifier the
    engine has to agree with.

    Args:
        entry_point: Absolute path to the configuration's `__init__.py`.
        directory: The configuration directory, used to give the module a stable name.

    Returns:
        Any: The imported module.

    Raises:
        ImportError: If the module cannot be loaded.
    """
    module_name = "_configuration_" + re.sub(r"\W", "_", os.path.abspath(directory))
    spec = importlib.util.spec_from_file_location(module_name, entry_point)
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
    if not name or os.path.sep in name or name in (".", ".."):
        raise ValueError(f"{name!r} is not a configuration name")
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
