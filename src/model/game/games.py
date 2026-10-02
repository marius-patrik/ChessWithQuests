"""Locating the shipped game configurations.

`games/` sits outside the package, so an installed distribution has to be able to find
its own default configuration without anyone passing it a path. This module is the one
place that knows where that directory is.
"""

import os
from typing import List

#: Name of the configuration a game runs when the player selects nothing.
DEFAULT_GAME = "chess"


def games_root() -> str:
    """Return the absolute path of the shipped `games/` directory.

    The directory is resolved relative to this module, so the answer is the same whether
    the project runs from a source checkout or from an installed distribution.

    Returns:
        str: Absolute path to the directory holding the shipped configurations.
    """
    package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(package_root, "games")


def available_games() -> List[str]:
    """Return the names of every shipped configuration.

    Returns:
        List[str]: Configuration directory names, with the default first, then the rest
        sorted. An empty list is returned when the `games/` directory is absent.
    """
    root = games_root()
    if not os.path.isdir(root):
        return []
    names = [
        name
        for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name)) and not name.startswith(("_", "."))
    ]
    others = sorted(name for name in names if name != DEFAULT_GAME)
    if DEFAULT_GAME in names:
        return [DEFAULT_GAME, *others]
    return others


def configuration_path(name: str) -> str:
    """Return the absolute path of one configuration directory.

    Args:
        name: Configuration directory name, for example `chess`.

    Returns:
        str: Absolute path to the configuration directory.

    Raises:
        FileNotFoundError: If no such configuration directory is shipped.
    """
    path = os.path.join(games_root(), name)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"no shipped game configuration named {name!r} in {games_root()}")
    return path
