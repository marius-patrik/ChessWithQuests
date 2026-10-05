"""The checkers board: eight by eight, the dark squares, and where the twelve start.

This is the checkers configuration speaking about its own board. The engine's `Board` knows
how to hold a rectangle of pieces and nothing else, so only this file knows that English
draughts is played on the dark squares of an eight by eight board, that a square is one of
those squares exactly when its row and column sum to an odd number, and who stands where on
the first move.

Row zero is White's side and row seven is Black's, which is the order the rest of this engine
already uses and the order a piece's declared forward vector points in: White's declared
diagonals have a positive row offset, so White moves towards row seven and a White man is
crowned on row seven. Nothing here knows the word "rank".

**The numbering one to thirty-two is here**, because it is a fact about this board rather
than about any notation, and it is *derived* from the one fact above rather than written out:
the played squares in board order, numbered from one. Counting them is what produces square
one on White's back row and square thirty-two on the crown row, so there is no second table
anywhere that could disagree with `is_played_square`. `games/checkers/export/letter.py` writes
moves in this naming and `CheckersBoard` draws the board edge in it, and both ask this module
rather than repeating it.

What is *not* here is a position grammar. The numbers name squares; they do not describe a
position, and `games/checkers/export/__init__.py` gives the long argument for why a draughts
game has no position record. Addressing a square as `(row, col)` remains true of every square
in the engine, and this numbering is a second name for the same place rather than a
replacement for it.
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


def square_number(row: int, col: int, rows: int = DIMENSIONS[0], cols: int = DIMENSIONS[1]) -> int:
    """Return the number a draughts player calls a square by.

    The numbering is the played squares counted in board order from one, which is what makes
    one to four White's back row and twenty-nine to thirty-two the crown row. It is *counted*
    rather than written out, so it cannot disagree with `is_played_square`: change which
    squares are played and the numbers follow, because there is no second table to change
    with them.

    Args:
        row: Zero-based row index.
        col: Zero-based column index.
        rows: Rows the board has.
        cols: Columns the board has.

    Returns:
        int: The square's number, counting from one.

    Raises:
        ValueError: If the coordinate is outside the board, or is one of the light squares
            the game is not played on. A light square has no number in this game's naming,
            and handing one back would put a name on a place no piece can ever stand.
    """
    if not (0 <= row < rows and 0 <= col < cols):
        raise ValueError(f"({row}, {col}) is not on a {rows}x{cols} draughts board")
    if not is_played_square(row, col):
        raise ValueError(
            f"({row}, {col}) is a light square; English draughts numbers only the squares "
            "the game is played on"
        )
    return sum(
        1
        for earlier_row in range(rows)
        for earlier_col in range(cols)
        if is_played_square(earlier_row, earlier_col) and (earlier_row, earlier_col) <= (row, col)
    )


class CheckersBoard(Board):
    """A draughts board, whose columns are named by the square numbers they hold.

    The engine's `Board` numbers its columns and every other board does the same. This one
    names them the way this game names its squares, which is why the window draws draughts
    numbers along its edge rather than digits that mean nothing here.
    """

    def file_label(self, col: int) -> str:
        """Return what this board calls the column at `col`.

        A draughts column holds four numbered squares and has no name of its own, so the
        label names the first of them counted from White's side — the square at the top of
        that column, which is the one a player reading the edge meets first. Writing all four
        would be more complete and wider than a square; a column's own index would name
        nothing a draughts player uses.

        Args:
            col: The column's 0-indexed number.

        Returns:
            str: The number of the first square in that column, in this game's naming.
        """
        numbers = [
            square_number(row, col, self.rows, self.cols)
            for row in range(self.rows)
            if is_played_square(row, col)
        ]
        return str(numbers[0]) if numbers else super().file_label(col)


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
        CheckersBoard: An eight by eight board holding the dark squares, with twelve men a
        side, whose columns are named by this game's square numbers.

    Raises:
        ValueError: If the board cannot hold the standard starting position.
    """
    return CheckersBoard((rows, cols), placement=starting_placement(rows, cols))


__all__ = [
    "BLACK_ROWS",
    "CheckersBoard",
    "DIMENSIONS",
    "PIECES_PER_SIDE",
    "WHITE_ROWS",
    "build_board",
    "is_played_square",
    "played_squares",
    "square_number",
    "starting_placement",
]
