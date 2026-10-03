"""The chess pieces: one file per piece, and the catalogue chess plays with.

`PIECES` is the list of what chess has, written out rather than discovered. The engine reads
it through `Configuration.pieces` so that a configuration can say what pieces it offers
without every consumer reaching into `games.chess.pieces` by name.
"""

from typing import List, Tuple, Type

from model.pieces.piece import Piece

from .bishop import Bishop
from .king import King
from .knight import Knight
from .pawn import Pawn
from .queen import Queen
from .rook import Rook

#: Every piece class chess offers, in no particular order.
PIECES: Tuple[Type[Piece], ...] = (Bishop, Knight, King, Pawn, Queen, Rook)


def build_pieces() -> List[Type[Piece]]:
    """Return the piece classes the chess configuration offers.

    Returns:
        List[Type[Piece]]: A fresh list of chess's piece classes, so a caller that edits the
        list it is handed cannot edit this catalogue.
    """
    return list(PIECES)
