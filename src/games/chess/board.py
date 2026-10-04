"""The chess board: eight by eight, and where the pieces start.

This is the chess configuration speaking about its own board. The engine's `Board` knows how
to hold a rectangle of pieces; only this file knows what a chess board is, how big it is, and
who stands where on the first move.

Every import here is relative. A configuration is a directory that can be copied to create a
variant, and an absolute `games.chess.…` import would leave a copy loading the pieces of the
original: a variant that looks edited and plays the original.
"""

from typing import List, Tuple

from model.game.board import Board
from model.pieces.piece import Piece

from .export.algebraic import file_letter
from .pieces.bishop import Bishop
from .pieces.king import King
from .pieces.knight import Knight
from .pieces.pawn import Pawn
from .pieces.queen import Queen
from .pieces.rook import Rook

#: A chess board is eight ranks by eight files.
DIMENSIONS: Tuple[int, int] = (8, 8)

#: The pieces a chess back rank carries, in the order they stand on it.
BACK_RANK = (Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook)

#: The rank a pawn stands on, counted from White's side.
PAWN_ROW: int = 1


class ChessBoard(Board):
    """A board whose columns are named the way chess names its files.

    The engine's `Board` numbers its columns, because a board knows how many it has and
    nothing about what they are called. Chess names them with letters, so the naming is
    declared here and the window draws whatever the board says — which is what keeps the view
    layer from importing this configuration to find out what to write along the bottom edge.
    """

    def file_label(self, col: int) -> str:
        """Return the letter chess names a file by.

        Args:
            col: The file's 0-indexed number.

        Returns:
            str: The file's letter, so the first column is `a`.
        """
        return file_letter(col)


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
        ChessBoard: An eight by eight board with White on the first two ranks and Black on the
        last two, whose files are named the way chess names them.

    Raises:
        ValueError: If the board cannot hold the chess starting position.
    """
    return ChessBoard((rows, cols), placement=starting_placement(rows, cols))
