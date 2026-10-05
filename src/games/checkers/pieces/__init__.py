"""The checkers pieces: one file per entry.

Two kinds, and the engine has never heard of either. `man.py` declares the one-square
diagonal step and `king.py` declares the slide; everything else about them — how they take,
when they are crowned, how many of a side may exist — is a rule, in `games/checkers/rules/`.

The catalogue is this directory. `build_pieces()` below hands this package to
`model.game.configuration.compose_section`, which returns one class per `Piece` subclass the files
here declare, so a third kind written into `pieces/` is offered because it is a file in `pieces/`.
The entries are classes rather than instances because a piece is placed by a board with a colour
and a square, so what a configuration offers is the class and the board builds one of them per
piece.
"""

import sys
from typing import List, Optional, Type

from model.game.configuration import compose_section
from model.pieces.piece import Piece


def build_pieces(notes: Optional[List[str]] = None) -> List[Type[Piece]]:
    """Return the piece classes this configuration offers.

    Args:
        notes: A list to record one line in per file that declares no piece, so the settings
            form can name it. Defaults to None, which discards them.

    Returns:
        List[Type[Piece]]: One class per `Piece` subclass the files in `pieces/` declare, in
        the order `compose_section` composes them: this package first, then the remaining files
        by name. The order is the order the settings form lists the pieces in and nothing
        depends on it otherwise — the board places what it is told to.
    """
    return compose_section(sys.modules[__name__], notes)
