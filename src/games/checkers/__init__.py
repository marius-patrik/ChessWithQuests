"""The checkers configuration: English draughts, shipped with the package.

`board.py` declares the rows, columns, the dark squares and the starting placement;
`pieces/`, `rules/`, `quests/`, `clocks/` and `export/` hold one file per entry. Nothing in
it says "checkers" to the engine: it is a board, two piece kinds and eight rules, composed
out loud below, and the engine reads none of them by name.

Composition is explicit. `build_configuration()` is the whole list of what this game is —
there is no registry, nothing is discovered by name, and a rule that is not named here is
not in force. This is the proof the abstraction was for: `chess` and `checkers` are two
directories and one engine, and nothing under `model/`, `controller/` or `view/` changed to
make the second one exist. The configuration imports itself by relative path throughout, so
`cp -r games/checkers games/house` produces a directory that plays *its own* rules rather
than these.

Three things are worth stating here rather than leaving to be discovered:

- **There is no royal piece.** A king in this game is a man that has been crowned, and it is
  taken like any other piece, so nothing declares a royal kind and the engine's check
  machinery correctly finds nothing to do.
- **The king flies.** The WCDF rulebook's English draughts king steps one square; this one
  slides any distance, which is international, Brazilian, Czech and Dutch draughts. The
  difference is one line in `pieces/king.py` and is documented there. What is gated by the
  published perft counts in `tests/test_draughts_perft.py` is the flying game.
- **No man is removed.** A man that reaches the far row is crowned and keeps playing; the
  only ways out of the game are losing every piece, being unable to move, and the draws.
"""

from model.game.configuration import Configuration

from .board import build_board
from .clocks.fischer import Fischer
from .pieces.king import King
from .pieces.man import Man
from .quests import build_quests
from .rules import build_rules

#: The name this configuration is loaded by.
NAME: str = "checkers"


def build_configuration() -> Configuration:
    """Assemble the checkers configuration.

    Returns:
        Configuration: The checkers board, and the pieces, rules, quests, clocks and
        exporters it brings with it.
    """
    return Configuration(
        name=NAME,
        path="",
        board=build_board(),
        pieces=[Man, King],
        rules=build_rules(),
        quests=build_quests(),
        clocks=[Fischer()],
        exporters=[],
        board_factory=build_board,
    )
