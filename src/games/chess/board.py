"""The chess board: eight by eight, and where the pieces start.

This is the chess configuration speaking about its own board. The engine's `Board` knows how
to hold a rectangle of pieces; only this file knows what a chess board is, how big it is, and
who stands where on the first move.
"""

from typing import List, Tuple

from model.game.board import Board
from model.pieces.piece import Piece
from games.chess.pieces.bishop import Bishop
from games.chess.pieces.horse import Horse
from games.chess.pieces.king import King
from games.chess.pieces.pawn import Pawn
from games.chess.pieces.queen import Queen
from games.chess.pieces.rook import Rook

#: A chess board is eight ranks by eight files.
DIMENSIONS: Tuple[int, int] = (8, 8)

#: The pieces a chess back rank carries, in the order they stand on it.
BACK_RANK = (Rook, Horse, Bishop, Queen, King, Bishop, Horse, Rook)

#: The rank a pawn stands on, counted from White's side.
PAWN_ROW: int = 1


def starting_placement(
    rows: int = DIMENSIONS[0], cols: int = DIMENSIONS[1]
) -> List[Tuple[Tuple[int, int], Piece]]:
    """Return the position a chess game starts from.

    Args:
        rows: Ranks the board has.
        cols: Files the board has.

    Returns:
        List[Tuple[Tuple[int, int], Piece]]: (position, piece) pairs, White first and Black
        last, each side a back rank with a rank of pawns in front of it.

    Raises:
        ValueError: If the board is not wide enough to hold a chess back rank, or too short
            to hold both sides' pawns. A board of any other size is legal and playable; it
            simply has no chess starting position, and saying so beats handing back a
            position that does not fit.
    """
    if cols != len(BACK_RANK):
        raise ValueError(
            f"the chess starting position describes a board {len(BACK_RANK)} files wide, "
            f"not one {cols} files wide"
        )
    if rows < 2 * PAWN_ROW + 2:
        raise ValueError(
            f"the chess starting position needs at least {2 * PAWN_ROW + 2} ranks, " f"not {rows}"
        )

    placement: List[Tuple[Tuple[int, int], Piece]] = [
        ((PAWN_ROW - 1, file), piece(1)) for file, piece in enumerate(BACK_RANK)
    ]
    placement += [((PAWN_ROW, file), Pawn(1)) for file in range(cols)]

    last_row = rows - 1
    last_pawn_row = rows - 1 - PAWN_ROW
    placement += [((last_row, file), piece(-1)) for file, piece in enumerate(BACK_RANK)]
    placement += [((last_pawn_row, file), Pawn(-1)) for file in range(cols)]
    return placement


def build_board(rows: int = DIMENSIONS[0], cols: int = DIMENSIONS[1]) -> Board:
    """Build a chess board with the standard starting position.

    Args:
        rows: Ranks the board has.
        cols: Files the board has.

    Returns:
        Board: An eight by eight board with White on the first two ranks and Black on the
        last two.

    Raises:
        ValueError: If the board cannot hold the chess starting position.
    """
    return Board((rows, cols), placement=starting_placement(rows, cols))
