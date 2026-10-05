"""The chess pieces: one file per piece, and the catalogue chess plays with.

The catalogue is this directory. `build_pieces()` below hands this package to
`model.game.configuration.compose_section`, which returns one class per `Piece` subclass the files
here declare, so a piece written into `pieces/` is in the catalogue because it is a file in
`pieces/`. What this returned instead was a literal `PIECES` tuple: the editor wrote a player's
piece, checked it, reported no problems, and the board was offered the original six.

Composition is over this package rather than over a name, because this directory can be copied.
`cp -r games/chess games/house` must offer the copy's pieces, not these — and the entries are
classes rather than instances because a piece is placed by a board with a colour and a square, so
what a configuration offers is the class and the board builds one of them per piece.
"""

import sys
from typing import List, Optional, Type

from model.game.configuration import compose_section
from model.pieces.piece import Piece


def build_pieces(notes: Optional[List[str]] = None) -> List[Type[Piece]]:
    """Return the piece classes the chess configuration offers.

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
