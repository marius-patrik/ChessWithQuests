"""The chess configuration: the default game, shipped with the package.

`board.py` declares the rows, columns and starting placement; `pieces/`, `rules/`,
`quests/`, `clocks/` and `export/` hold one file per entry. It is the default configuration
and cannot be edited or deleted: a variant starts by duplicating it.

Composition is explicit. `build_configuration()` below is the whole list of what chess is —
there is no registry, nothing is discovered by name, and a rule that is not named here is
not in force.

Every import below is relative, and that is load-bearing rather than stylistic. This directory
is a copyable unit: `cp -r games/chess games/house` and a variant exists. An absolute
`games.chess.…` import inside a copy would still reach back here, so the copy would load this
board, these pieces and these rules while looking like it had loaded its own — silently, with
no error and no warning. `model/game/configuration.py` loads a configuration as a package in
its own right for the same reason.

One gap remains, and it is recorded in `notes/object_model.md`: the modules under
`games/chess/rules/` still import each other by absolute path, so a copy currently shares
chess's rules with the original. Their imports are the last chess coupling in the tree.
"""

from typing import Any, List

from model.game.configuration import Configuration
from model.game.games import DEFAULT_GAME
from model.game.quest import Quest
from model.game.rule import Rule
from model.misc.export_writers import ChessNotationWriter

from .board import build_board
from .clocks.fischer import Fischer
from .pieces import build_pieces
from .rules import build_rules


def build_exporters() -> List[Any]:
    """Build the export writers chess offers.

    The chess formats — PGN, FEN and the stenographic coordinate record — are chess formats,
    and `notes/object_model.md` registers that they belong to a configuration. The writer
    class itself still lives in the engine module `model.misc.export_writers` because
    `model/game/manager.py` imports it by name; this function is where that import is
    isolated, so moving the class needs one line changed rather than a search.

    Returns:
        List[Any]: One writer for the chess configuration.
    """
    return [ChessNotationWriter()]


def build_configuration() -> Configuration:
    """Assemble the chess configuration.

    Returns:
        Configuration: The chess board, and the pieces, rules, quests, clocks and exporters
        chess brings with it.
    """
    return Configuration(
        name=DEFAULT_GAME,
        path="",
        board=build_board(),
        pieces=build_pieces(),
        rules=build_rules(),
        quests=build_quests(),
        clocks=[Fischer()],
        exporters=build_exporters(),
        board_factory=build_board,
    )


def build_quests() -> List[Quest]:
    """Build the quests chess offers by default.

    `CaptureOfType` and `KingOnlyGame` are here rather than in `model/game/quests.py`'s
    roster, because both insist on naming a piece type and only chess can say which one. The
    engine holds the classes and the parameters; this is where the answers live.

    Returns:
        List[Quest]: A small starter set, all of them switchable from the settings form.
    """
    from model.game.quests import (
        CaptureN,
        CaptureOfType,
        FirstBlood,
        KingOnlyGame,
        MakeCheckN,
        WonBy,
    )

    return [
        FirstBlood(reward=25),
        CaptureN(count=5, reward=50),
        CaptureOfType(piece_type="queen", count=1, reward=45),
        MakeCheckN(count=3, reward=40),
        KingOnlyGame(royal_kind="king", reward=60),
        WonBy(color=1, reward=75),
    ]
