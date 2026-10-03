"""The checkers board: eight by eight, the dark squares, and where the twelve start.

This is the checkers configuration speaking about its own board. The engine's `Board` knows
how to hold a rectangle of pieces and nothing else, so only this file knows that English
draughts is played on the dark squares of an eight by eight board, that a square is one of
those squares exactly when its row and column sum to an odd number, and who stands where on
the first move.

Row zero is White's side and row seven is Black's, which is the order the rest of this engine
already uses and the order a piece's declared forward vector points in: White's declared
diagonals have a positive row offset, so White moves towards row seven and a White man is
crowned on row seven. Nothing here knows the word "rank" or the numbering one to thirty-two;
a draughts position has neither, and the squares are addressed as `(row, col)` like every
other square in the engine.
"""

from typing import Any, List, Tuple

from model.game.board import Board
from model.pieces.piece import Piece
from .pieces.man import Man

#: An English draughts board is eight rows by eight columns.
DIMENSIONS: Tuple[int, int] = (8, 8)

#: The three rows White's twelve men occupy, counted from White's own side.
WHITE_ROWS: Tuple[int, int, int] = (0, 1, 2)

#: The three rows Black's twelve men occupy.
BLACK_ROWS: Tuple[int, int, int] = (5, 6, 7)

#: How many pieces a side starts with.
PIECES_PER_SIDE: int = 12


def is_played_square(row: int, col: int) -> bool:
    """Report whether a coordinate is one of the squares the game is played on.

    English draughts uses half of the squares of the board, and which half is a property of
    the board rather than of any piece. A square is played when its row and column sum to an
    odd number, which makes row zero's played squares the odd columns — so the two colours
    start on opposite parities of every row they share, and a piece on a played square is
    always diagonal to four others and never to eight.

    Args:
        row: Zero-based row index.
        col: Zero-based column index.

    Returns:
        bool: True when the square is one the game is played on, False otherwise.
    """
    return (row + col) % 2 == 1


def played_squares(position: Any) -> List[Tuple[int, int]]:
    """List every square of a board that the game is played on.

    Args:
        position: The board to read, for its dimensions.

    Returns:
        List[Tuple[int, int]]: The played squares, in board order.
    """
    return [
        (row, col)
        for row in range(position.rows)
        for col in range(position.cols)
        if is_played_square(row, col)
    ]


def starting_placement(
    rows: int = DIMENSIONS[0], cols: int = DIMENSIONS[1]
) -> List[Tuple[Tuple[int, int], Piece]]:
    """Return the position a game of English draughts starts from.

    Each side fills the three rows nearest its own edge, four pieces to a row, and there is
    nothing on the two rows in between. Twelve a side.

    Args:
        rows: Rows the board has.
        cols: Columns the board has.

    Returns:
        List[Tuple[Tuple[int, int], Piece]]: (position, piece) pairs, White first and Black
        last, each side three full rows of twelve men.

    Raises:
        ValueError: If the board is not eight by eight. The starting position of English
            draughts is defined for one board and one only, and handing back twelve pieces
            on a board that cannot hold them would be worse than refusing.
    """
    if (rows, cols) != DIMENSIONS:
        raise ValueError(
            f"the English draughts starting position describes a board "
            f"{DIMENSIONS[0]}x{DIMENSIONS[1]}, not one {rows}x{cols}"
        )

    placement: List[Tuple[Tuple[int, int], Piece]] = [
        ((row, col), Man(1))
        for row in WHITE_ROWS
        for col in range(cols)
        if is_played_square(row, col)
    ]
    placement += [
        ((row, col), Man(-1))
        for row in BLACK_ROWS
        for col in range(cols)
        if is_played_square(row, col)
    ]
    return placement


def build_board(rows: int = DIMENSIONS[0], cols: int = DIMENSIONS[1]) -> Board:
    """Build a checkers board with the standard starting position.

    Args:
        rows: Rows the board has.
        cols: Columns the board has.

    Returns:
        Board: An eight by eight board holding the dark squares, with twelve men a side.

    Raises:
        ValueError: If the board cannot hold the standard starting position.
    """
    return Board((rows, cols), placement=starting_placement(rows, cols))


__all__ = [
    "BLACK_ROWS",
    "DIMENSIONS",
    "PIECES_PER_SIDE",
    "WHITE_ROWS",
    "build_board",
    "is_played_square",
    "played_squares",
    "starting_placement",
]
