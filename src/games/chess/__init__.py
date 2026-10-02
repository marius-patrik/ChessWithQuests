"""The chess configuration: the default game, shipped with the package.

`board.py` declares the rows, columns and starting placement; `pieces/`, `rules/`,
`quests/`, `clocks/` and `export/` hold one file per entry. It is the default configuration
and cannot be edited or deleted: a variant starts by duplicating it.

Composition is explicit. `build_configuration()` below is the whole list of what chess is —
there is no registry, nothing is discovered by name, and a rule that is not named here is
not in force.
"""

from model.game.configuration import Configuration
from model.game.games import DEFAULT_GAME
from games.chess.board import DIMENSIONS, build_board


def build_configuration() -> Configuration:
    """Assemble the chess configuration.

    Returns:
        Configuration: The chess board, and the rules, quests, clocks and exporters chess
        brings with it.
    """
    return Configuration(
        name=DEFAULT_GAME,
        path="",
        board=build_board(),
        pieces=[],
        rules=[],
        quests=[],
        clocks=[],
        exporters=[],
    )
