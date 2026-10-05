"""Locating the shipped game configurations.

`games/` sits outside the package, so an installed distribution has to be able to find
its own configurations without anyone passing it a path. This module is the one place that
knows where that directory is, and it is the one place that knows **which of the
configurations in it a game starts in** — which is a fact about what the distribution ships
rather than about any one configuration, and is declared beside them in `default.json`.

Why it is declared there and not inside a configuration is worth one paragraph, because it is
the whole of the reasoning. A configuration is copied to make a variant, and a copy is
byte-identical to its original: whatever a configuration said about itself, its copy says too.
So a declaration *inside* a configuration cannot distinguish the original from its copy, and a
variant would either be protected against edits it must be free to make or the original would
be editable. The name of the default is therefore something the root names, and the engine
holds no game name of its own — which is what `SCRATCHPAD.md` constraint 1.4 asks for and what
`tests/test_engine_holds_no_chess.py` now walks the tree to prove.
"""

import json
import os
from typing import List, Optional

#: The file, in a configurations root, that names the configuration a game starts in when the
#: player selects nothing. Its content is a JSON object with a `configuration` key. A root that
#: declares none still has to answer, so the first configuration it ships is used and nothing
#: is protected — nothing said which one to protect.
DEFAULT_DECLARATION = "default.json"

#: The key in the declaration that holds the name.
DEFAULT_DECLARATION_KEY = "configuration"


def games_root() -> str:
    """Return the absolute path of the shipped `games/` directory.

    The directory is resolved relative to this module, so the answer is the same whether
    the project runs from a source checkout or from an installed distribution.

    Returns:
        str: Absolute path to the directory holding the shipped configurations.
    """
    package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(package_root, "games")


def default_configuration_name(root: Optional[str] = None) -> Optional[str]:
    """Return the name of the configuration a game starts in when the player selects nothing.

    Read from the declaration in the root rather than from any configuration, and read without
    importing anything: the answer is needed by the operations that must never fail for want of
    it — a variant whose rules do not import has to remain deletable — so it cannot depend on a
    configuration loading.

    Args:
        root: The directory configurations must live under. Defaults to the shipped `games/`.

    Returns:
        Optional[str]: The declared name, or None when the root declares none or the
        declaration cannot be read. None is not an error: a distribution is free to ship
        configurations without saying which one it starts in.
    """
    declaration = os.path.join(os.path.abspath(root or games_root()), DEFAULT_DECLARATION)
    try:
        with open(declaration, encoding="utf-8") as handle:
            declared = json.load(handle)
    except (OSError, ValueError):
        # A missing root, a missing declaration, and a declaration that is not JSON are all the
        # same answer: nothing has said which configuration is the default.
        return None
    if not isinstance(declared, dict):
        return None
    name = declared.get(DEFAULT_DECLARATION_KEY)
    return str(name) if isinstance(name, str) and name else None


def available_games(root: Optional[str] = None) -> List[str]:
    """Return the names of every shipped configuration.

    Args:
        root: The directory configurations must live under. Defaults to the shipped `games/`.

    Returns:
        List[str]: Configuration directory names, the one the root declares as its default
        first, then the rest sorted. An empty list is returned when the directory is absent.
    """
    directory = os.path.abspath(root or games_root())
    if not os.path.isdir(directory):
        return []
    names = [
        name
        for name in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, name)) and not name.startswith(("_", "."))
    ]
    declared = default_configuration_name(directory)
    others = sorted(name for name in names if name != declared)
    if declared in names:
        return [declared, *others]
    return others


def configuration_path(name: str) -> str:
    """Return the absolute path of one configuration directory.

    Args:
        name: Configuration directory name.

    Returns:
        str: Absolute path to the configuration directory.

    Raises:
        FileNotFoundError: If no such configuration directory is shipped.
    """
    path = os.path.join(games_root(), name)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"no shipped game configuration named {name!r} in {games_root()}")
    return path
