"""A draughts board labels its own columns, in the numbering it counts from the board.

`Board.file_label` numbers a column by default and `games/chess/board.py`'s `ChessBoard`
overrides that with the algebraic letter. `games/checkers/board.py`'s `CheckersBoard`
overrides it the same way, with this game's square numbers — so a draughts window draws
draughts numbers along its edge instead of digits that mean nothing to a player of it. A
draughts column holds four numbered squares and has no name of its own, so the label names
the first of them counted from White's side.

**The numbering is `square_number`**, counted from the squares the game is played on, and
every test here that names a square pins it against `tests/test_draughts_perft.py`'s
independent derivation of the same arrangement.
"""

import pytest

from games.checkers.board import build_board, square_number
from tests.test_draughts_perft import coordinates, square_of

# --- the numbering, which is the board's and the perft gate's at once


def test_the_board_numbers_its_squares_the_way_draughts_does():
    """One to four is White's back row, twenty-nine to thirty-two the crown row.

    Both ends and the count, because a numbering that starts at one and ends at thirty-two is
    not the same thing as the standard arrangement.

    Returns:
        None
    """
    assert square_number(0, 1) == 1
    assert square_number(0, 7) == 4
    assert square_number(7, 0) == 29
    assert square_number(7, 6) == 32

    numbered = {
        square_number(row, col) for row in range(8) for col in range(8) if (row + col) % 2 == 1
    }
    assert numbered == set(range(1, 33))


def test_the_board_numbering_is_the_numbering_the_perft_gate_derives():
    """Two independent derivations of the arrangement, asserted equal for all thirty-two squares.

    `tests/test_draughts_perft.py` derives the numbering from the geometry of the dark squares
    on purpose, so that the published counts it is gated against cannot be restated in terms
    of whatever the game happens to implement. This is the assertion that keeps the production
    numbering from drifting away from it.

    Returns:
        None
    """
    for square in range(1, 33):
        assert square_number(*coordinates(square)) == square
        assert square_of(*coordinates(square)) == square


def test_a_light_square_has_no_number_and_says_so():
    """A square no piece can stand on has no name in this game's numbering.

    Returns:
        None
    """
    with pytest.raises(ValueError, match="light square"):
        square_number(0, 0)

    with pytest.raises(ValueError, match="not on"):
        square_number(8, 1)


# --- the board's own column labels


def test_a_draughts_board_names_its_columns_with_square_numbers():
    """The window draws what the board says, so this is what a draughts player reads along the
    bottom edge: the numbers of the squares that column holds, not 1 to 8.

    Returns:
        None
    """
    board = build_board()

    assert board.file_label(0) == "5"
    assert board.file_label(1) == "1"
    assert board.file_label(7) == "4"
    assert [board.file_label(col) for col in range(8)] != [str(col + 1) for col in range(8)]


def test_the_column_labels_are_the_squares_the_board_actually_numbers():
    """Every label is a real square number of that column, and the first one from White's side.

    Returns:
        None
    """
    board = build_board()

    for col in range(board.cols):
        numbers = [square_number(row, col) for row in range(board.rows) if (row + col) % 2 == 1]
        assert board.file_label(col) == str(numbers[0])
